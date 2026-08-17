"""FastAPI Web 层：把面试暴露为 HTTP 接口 + 静态前端。"""
from __future__ import annotations

import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

load_dotenv()

from .config import load_config
from .engine import InterviewEngine
from .llm import LLMClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "dimensions.yaml"
INDEX_PATH = PROJECT_ROOT / "web" / "index.html"

config = load_config(str(CONFIG_PATH))
try:
    llm = LLMClient()
    _llm_error: str | None = None
except RuntimeError as e:
    llm = None
    _llm_error = str(e)

# 会话存储（内存态，MVP 够用；重启即清空）
sessions: dict[str, InterviewEngine] = {}

app = FastAPI(title="PersonaCore")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    if not INDEX_PATH.exists():
        return "<h1>前端页面缺失，请检查 web/index.html</h1>"
    return INDEX_PATH.read_text(encoding="utf-8")


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
def post_message(sid: str, body: MessageIn) -> dict:
    engine = sessions.get(sid)
    if engine is None:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if engine.finished:
        raise HTTPException(status_code=400, detail="面试已结束")
    reply = engine.send(body.message)
    return {"message": reply, "finished": engine.finished}


@app.get("/interview/{sid}/report")
def get_report(sid: str) -> dict:
    engine = sessions.get(sid)
    if engine is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not engine.finished:
        raise HTTPException(status_code=409, detail="面试尚未结束")
    result = engine.finalize()
    return {"markdown": result.full_markdown(), "json": result.to_dict()}
