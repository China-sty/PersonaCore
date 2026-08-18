"""管理员面板冒烟测试：登录鉴权 + 候选人列表 + 报告查看（无需 API Key）。"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import personacore.web as web
from fastapi.testclient import TestClient
from personacore.llm import LLMClient


class FakeLLM(LLMClient):
    def __init__(self):
        self.api_key = "fake"
        self.base_url = "fake"
        self.model = "fake"
        self.client = None

    def chat(self, messages, temperature=0.3, max_tokens=2000):
        return "候选人整体表现均衡。"

    def chat_json(self, messages, temperature=0.0):
        return {"score": 4.0, "confidence": 0.8, "evidence": ["证据"], "rationale": "合理"}

    def chat_structured(self, messages, result_cls, temperature=0.0):
        if result_cls.__name__ == "FollowupDecision":
            return result_cls(done=True, question="")
        return result_cls(score=4.0, confidence=0.8, evidence=["证据"], rationale="合理")


def main() -> None:
    web.llm = FakeLLM()
    # 用临时库，避免污染真实数据
    tmp = tempfile.mkdtemp()
    web.store = web.Store(os.path.join(tmp, "test.db"))

    client = TestClient(web.app)

    # 完整面试 + 报告（触发落库）
    sid = client.post("/interview/start").json()["session_id"]
    for _ in range(6):
        r = client.post(f"/interview/{sid}/message", data={"message": "我有具体例子，负责排期并按时交付"})
        if r.json()["finished"]:
            break
    assert client.get(f"/interview/{sid}/report").status_code == 200

    # 未登录 -> 401
    assert client.get("/admin/api/candidates").status_code == 401
    # 错误密码 -> 401
    assert client.post("/admin/login", json={"password": "wrong"}).status_code == 401
    # 正确密码 -> 200
    assert client.post("/admin/login", json={"password": "admin123"}).status_code == 200

    # 列表
    r = client.get("/admin/api/candidates")
    assert r.status_code == 200
    lst = r.json()
    assert len(lst) >= 1 and "composite" in lst[0] and "decision" in lst[0]

    # 详情
    rid = lst[0]["id"]
    r = client.get(f"/admin/api/candidates/{rid}")
    assert r.status_code == 200
    assert "综合得分" in r.json()["report_md"]

    print("ADMIN SMOKE OK —— 登录/列表/报告查看 全流程跑通")


if __name__ == "__main__":
    main()
