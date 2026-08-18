"""Web 层冒烟测试：用假 LLM 走通 start → message → report 全流程（无需 API Key）。"""
from __future__ import annotations

import sys
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


def main() -> None:
    web.llm = FakeLLM()  # 替换为假 LLM
    client = TestClient(web.app)

    # 首页
    assert client.get("/").status_code == 200

    # 开始面试
    r = client.post("/interview/start")
    assert r.status_code == 200, r.text
    data = r.json()
    sid = data["session_id"]
    assert len(data["messages"]) == 2

    # 逐条回答直到结束
    answers = iter(["答1", "答2", "答3", "答4", "答5", "答6", "答7", "答8", "答9", "答10"])
    finished = False
    for _ in range(20):
        r = client.post(f"/interview/{sid}/message", data={"message": next(answers, "记不清了")})
        assert r.status_code == 200, r.text
        if r.json()["finished"]:
            finished = True
            break
    assert finished, "面试未按预期结束"

    # 报告
    r = client.get(f"/interview/{sid}/report")
    assert r.status_code == 200, r.text
    rep = r.json()
    assert "综合得分" in rep["markdown"]
    assert rep["json"]["decision"] in ("通过", "待定", "淘汰")

    print("WEB SMOKE OK —— start/message/report 全流程跑通")


if __name__ == "__main__":
    main()
