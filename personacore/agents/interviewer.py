"""面试官 Agent：主持结构化面试，按维度提问并对回答是否充分做追问判断。"""
from __future__ import annotations

from typing import Dict, List

from ..config import Dimension
from ..llm import LLMClient
from ._util import format_turns

_FOLLOWUP_SYSTEM = """你是一位专业的结构化行为面试官，正在测评候选人「{dim_name}」（大五人格 {bigfive}）。
正向行为锚点：{pos}
负向行为锚点：{neg}

判断候选人的回答是否已经包含足够的具体行为证据（最好符合 STAR：情境、任务、行动、结果）。
- 若证据已充分（有具体事例、具体行动与结果），done 设为 true，question 设为空字符串。
- 若证据不足（过于笼统、停留在观点或"我们一般会怎么做"），done 设为 false，question 给出一句简短追问，引导对方补充具体行为细节；追问要自然、中立，不暗示"正确答案"。

严格只输出 JSON（不要输出任何其他文字），字段：
{{"done": <true 或 false>, "question": "<追问内容，若 done 为 true 则给空字符串>"}}"""


class Interviewer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def opening(self) -> str:
        return (
            "你好，感谢参加本次测评。接下来我会和你聊几个关于过往经历和做法的问题，"
            "请尽量用具体的事例回答（当时的情境、你做了什么、结果如何）。"
        )

    def closing(self) -> str:
        return "感谢你的分享，本次测评到这里就结束了。"

    def decide_followup(self, dim: Dimension, turns: List[Dict[str, str]]) -> str:
        """返回 "DONE"（证据充分）或一句追问。"""
        system = _FOLLOWUP_SYSTEM.format(
            dim_name=dim.name,
            bigfive=dim.bigfive,
            pos="、".join(dim.anchors_positive),
            neg="、".join(dim.anchors_negative),
        )
        user = f"当前面试记录：\n{format_turns(turns)}\n\n请判断证据是否充分。"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        data = self.llm.chat_json(messages, temperature=0.2)
        done = bool(data.get("done", False))
        question = str(data.get("question", "")).strip()
        return "DONE" if done or not question else question
