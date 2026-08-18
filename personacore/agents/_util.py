"""智能体共用的工具函数。"""
from __future__ import annotations

from typing import Dict, List


def format_signals(signals: dict) -> str:
    """把语音信号 dict 渲染成一句话备注（供 LLM 作为辅助证据）。"""
    if not isinstance(signals, dict):
        return ""
    emotion = signals.get("emotion")
    if not emotion:
        return ""
    conf = signals.get("confidence")
    suffix = f"，置信度 {conf:.2f}" if isinstance(conf, (int, float)) else ""
    return f"　【语音情绪：{emotion}{suffix}】"


def format_turns(turns: List[Dict[str, str]]) -> str:
    """把问答轮次格式化为可读文本（含语音信号）。"""
    lines = []
    for t in turns:
        role = "面试官" if t["role"] == "interviewer" else "候选人"
        line = f"{role}: {t['content']}"
        line += format_signals(t.get("signals"))
        lines.append(line)
    return "\n".join(lines)
