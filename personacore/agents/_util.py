"""智能体共用的工具函数。"""
from __future__ import annotations

from typing import Dict, List


def format_turns(turns: List[Dict[str, str]]) -> str:
    """把问答轮次格式化为可读文本。"""
    lines = []
    for t in turns:
        role = "面试官" if t["role"] == "interviewer" else "候选人"
        lines.append(f"{role}: {t['content']}")
    return "\n".join(lines)
