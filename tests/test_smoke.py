"""端到端冒烟测试：用假 LLM 跑通「面试 → 分析 → 裁决 → 报告」闭环（无需 API Key）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from personacore.config import load_config
from personacore.llm import LLMClient
from personacore.orchestrator import Orchestrator

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class FakeLLM(LLMClient):
    def __init__(self):
        self.api_key = "fake"
        self.base_url = "fake"
        self.model = "fake"
        self.client = None

    def chat(self, messages, temperature=0.3, max_tokens=2000):
        sys_prompt = messages[0]["content"] if messages else ""
        if "追问" in sys_prompt:  # 面试官追问判断
            return "DONE"
        return "候选人整体表现均衡，具备较强的责任意识与协作能力，情绪较为稳定。"

    def chat_json(self, messages, temperature=0.0):
        return {
            "score": 4.0,
            "confidence": 0.8,
            "evidence": ["我在项目中负责排期并按时交付。"],
            "rationale": "有具体行动和结果，符合正向锚点。",
        }


def main() -> None:
    config = load_config(str(PROJECT_ROOT / "config" / "dimensions.yaml"))
    orch = Orchestrator(config, FakeLLM())

    answers = iter(
        [
            "我同时负责三个项目，用清单排优先级，全部按时交付。",
            "我和同事意见分歧，我主动沟通，最终达成一致。",
            "项目突发问题，我保持冷静，先拆解再逐步解决。",
            "我主动组织了跨部门协作活动，带动了大家参与。",
            "我主动学习了新工具并应用到项目中，提升了效率。",
        ]
    )
    result = orch.run(input_fn=lambda _: next(answers), output_fn=lambda _: None)

    report = result.full_markdown()
    for expected in ("综合得分", "尽责性", "宜人性", "情绪稳定性", "外向性", "开放性", "结论", "面试全记录"):
        assert expected in report, f"报告缺少: {expected}"
    assert ("通过" in report) or ("待定" in report) or ("淘汰" in report)
    assert result.to_dict()["decision"] in ("通过", "待定", "淘汰")

    print("SMOKE OK —— 闭环跑通\n")
    print(report)


if __name__ == "__main__":
    main()
