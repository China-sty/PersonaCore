"""FastAPI Web 层：面试接口 + 管理员面板 + 静态前端。"""
from __future__ import annotations

import os
import secrets
import threading
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

load_dotenv()

from .config import load_config
from .engine import InterviewEngine
from .llm import LLMClient
from .modalities.asr import DashscopeTranscriber, Transcriber
from .modalities.emotion import Emotion2vecRecognizer, EmotionRecognizer
from .store import Store

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "dimensions.yaml"
INDEX_PATH = PROJECT_ROOT / "web" / "index.html"
ADMIN_PATH = PROJECT_ROOT / "web" / "admin.html"
AUDIO_DIR = PROJECT_ROOT / "data" / "audio"

config = load_config(str(CONFIG_PATH))
try:
    llm = LLMClient()
    _llm_error: str | None = None
except RuntimeError as e:
    llm = None
    _llm_error = str(e)

store = Store()
sessions: dict[str, InterviewEngine] = {}

# 多模态能力（可插拔，未配置则降级为仅文字）
try:
    transcriber: Transcriber | None = DashscopeTranscriber()
except RuntimeError:
    transcriber = None
emotion_recognizer: EmotionRecognizer = Emotion2vecRecognizer()
# 后台预热情绪模型，避免第一个语音回答等待加载
threading.Thread(target=emotion_recognizer.warmup, daemon=True).start()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
_admin_tokens: set[str] = set()

app = FastAPI(title="PersonaCore")


def _finalize_and_save(sid: str, engine: InterviewEngine) -> None:
    result = engine.finalize()
    store.save(sid, result)


def save_audio(session_id: str, audio_bytes: bytes) -> str:
    """把候选人的音频回答落盘（记录/审计），返回保存路径。"""
    d = AUDIO_DIR / session_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.webm"
    path.write_bytes(audio_bytes)
    return str(path)


# ---- 前端页面 ----

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_PATH.read_text(encoding="utf-8")


@app.get("/admin", response_class=HTMLResponse)
def admin_page() -> str:
    return ADMIN_PATH.read_text(encoding="utf-8")


# ---- 管理员认证 ----

class PasswordIn(BaseModel):
    password: str


@app.post("/admin/login")
def admin_login(body: PasswordIn, response: Response) -> dict:
    if body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="密码错误")
    token = secrets.token_hex(16)
    _admin_tokens.add(token)
    response.set_cookie("admin_token", token, httponly=True, samesite="lax")
    return {"ok": True}


@app.post("/admin/logout")
def admin_logout(request: Request, response: Response) -> dict:
    token = request.cookies.get("admin_token")
    if token:
        _admin_tokens.discard(token)
    response.delete_cookie("admin_token")
    return {"ok": True}


def _require_admin(request: Request) -> None:
    token = request.cookies.get("admin_token")
    if not token or token not in _admin_tokens:
        raise HTTPException(status_code=401, detail="未登录")


# ---- 管理员数据接口 ----

@app.get("/admin/api/candidates")
def admin_candidates(request: Request) -> list:
    _require_admin(request)
    return store.list()


@app.get("/admin/api/candidates/{record_id}")
def admin_candidate(record_id: int, request: Request) -> dict:
    _require_admin(request)
    rec = store.get(record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return rec


# ---- 面试接口 ----

@app.post("/interview/start")
def start_interview() -> dict:
    if llm is None:
        raise HTTPException(status_code=500, detail=f"LLM 未配置：{_llm_error}")
    sid = uuid.uuid4().hex
    engine = InterviewEngine(config, llm)
    sessions[sid] = engine
    opening, first_q = engine.start()
    return {"session_id": sid, "messages": [opening, first_q]}


@app.post("/interview/{sid}/message")
def post_message(
    sid: str,
    background_tasks: BackgroundTasks,
    message: str = Form(None),
    audio: UploadFile = File(None),
) -> dict:
    engine = sessions.get(sid)
    if engine is None:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if engine.finished:
        raise HTTPException(status_code=400, detail="面试已结束")

    text = (message or "").strip()
    signals = None
    if audio is not None:
        audio_bytes = audio.file.read()
        save_audio(sid, audio_bytes)  # 先记录音频（审计）
        if transcriber is None:
            raise HTTPException(status_code=500, detail="未配置 ASR（DASHSCOPE_API_KEY），无法处理音频")
        text = transcriber.transcribe(audio_bytes)
        signals = emotion_recognizer.recognize(audio_bytes)

    if not text:
        raise HTTPException(status_code=400, detail="请提供文字或音频")

    reply = engine.send(text, signals)
    if engine.finished:
        # 面试结束：后台异步分析 + 落库，候选人无需等待
        background_tasks.add_task(_finalize_and_save, sid, engine)
    return {"message": reply, "finished": engine.finished, "asr_text": text}


@app.get("/interview/{sid}/report")
def get_report(sid: str) -> dict:
    engine = sessions.get(sid)
    if engine is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not engine.finished:
        raise HTTPException(status_code=409, detail="面试尚未结束")
    result = engine.finalize()
    store.save(sid, result)
    return {"markdown": result.full_markdown(), "json": result.to_dict()}
