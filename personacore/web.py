"""FastAPI Web 层：面试接口 + 管理员面板 + 静态前端。"""
from __future__ import annotations

import os
import secrets
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

load_dotenv()

from .config import load_config
from .engine import InterviewEngine
from .llm import LLMClient
from .store import Store

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "dimensions.yaml"
INDEX_PATH = PROJECT_ROOT / "web" / "index.html"
ADMIN_PATH = PROJECT_ROOT / "web" / "admin.html"

config = load_config(str(CONFIG_PATH))
try:
    llm = LLMClient()
    _llm_error: str | None = None
except RuntimeError as e:
    llm = None
    _llm_error = str(e)

store = Store()
sessions: dict[str, InterviewEngine] = {}

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
_admin_tokens: set[str] = set()

app = FastAPI(title="PersonaCore")


def _finalize_and_save(sid: str, engine: InterviewEngine) -> None:
    result = engine.finalize()
    store.save(sid, result)


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


class MessageIn(BaseModel):
    message: str


@app.post("/interview/{sid}/message")
def post_message(sid: str, body: MessageIn, background_tasks: BackgroundTasks) -> dict:
    engine = sessions.get(sid)
    if engine is None:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if engine.finished:
        raise HTTPException(status_code=400, detail="面试已结束")
    reply = engine.send(body.message)
    if engine.finished:
        # 面试结束：后台异步分析 + 落库，候选人无需等待
        background_tasks.add_task(_finalize_and_save, sid, engine)
    return {"message": reply, "finished": engine.finished}


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
