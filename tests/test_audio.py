"""音频链路冒烟测试：用 MockTranscriber 验证「音频→ASR→信号→engine」闭环。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import personacore.web as web
from fastapi.testclient import TestClient
from personacore.agents._util import format_signals, format_turns
from personacore.llm import LLMClient
from personacore.modalities.asr import MockTranscriber
from personacore.modalities.emotion import EmotionRecognizer


class FakeLLM(LLMClient):
    def __init__(self):
        self.api_key = "fake"
        self.base_url = "fake"
        self.model = "fake"
        self.client = None

    def chat(self, messages, temperature=0.3, max_tokens=2000):
        return "总体评价。"

    def chat_json(self, messages, temperature=0.0):
        return {"score": 4.0, "confidence": 0.8, "evidence": ["证据"], "rationale": "合理"}


class FakeEmotion(EmotionRecognizer):
    def recognize(self, audio, sample_rate=16000):
        return {"emotion": "平静", "confidence": 0.9}


def main() -> None:
    # 1. 信号渲染单元检查
    assert "平静" in format_signals({"emotion": "平静", "confidence": 0.9})
    turns = [
        {"role": "interviewer", "content": "问题"},
        {"role": "candidate", "content": "回答", "signals": {"emotion": "平静", "confidence": 0.9}},
    ]
    assert "语音情绪" in format_turns(turns)

    # 2. web 层音频上传闭环
    web.llm = FakeLLM()
    web.transcriber = MockTranscriber("我负责三个项目并按时交付")
    web.emotion_recognizer = FakeEmotion()
    client = TestClient(web.app)

    sid = client.post("/interview/start").json()["session_id"]
    r = client.post(
        f"/interview/{sid}/message",
        files={"audio": ("a.webm", b"\x00\x01fakeaudio", "audio/webm")},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["asr_text"] == "我负责三个项目并按时交付"
    assert data["finished"] is False

    print("AUDIO SMOKE OK —— 音频→ASR→信号→engine 闭环跑通")


if __name__ == "__main__":
    main()
