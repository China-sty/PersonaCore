"""维度分析师 Agent：每个大五维度一个，基于原文证据打分。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from ..config import Dimension
from ..llm import LLMClient
from ..models import DimensionAnalysis
from ._util import format_turns

_ANALYST_SYSTEM = """你是人格测评专家，专门评估大五人格中的「{dim_name}」（{bigfive}）。
正向行为锚点：{pos}
负向行为锚点：{neg}

请基于候选人的面试回答，评估该维度的得分（{scale_min}~{scale_max} 分，可用一位小数）。
规则：
- 只能依据回答原文中的证据，不得臆测，不得因"说得漂亮"就给高分。
- 若证据不足，请降低 confidence。
- 分数含义：{scale_min}=明显呈现负向锚点，{mid}=中性/信息不足，{scale_max}=明显呈现正向锚点。

请通过 respond 函数返回分析结果。"""


@dataclass
class DimensionResult:
    dimension_key: str
    name: str
    score: float
    confidence: float
    evidence: List[str] = field(default_factory=list)
    rationale: str = ""


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class Analyst:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze(
        self,
        dim: Dimension,
        turns: List[Dict[str, str]],
        scale_min: int,
        scale_max: int,
    ) -> DimensionResult:
        mid = (scale_min + scale_max) / 2
        system = _ANALYST_SYSTEM.format(
            dim_name=dim.name,
            bigfive=dim.bigfive,
            pos="、".join(dim.anchors_positive),
            neg="、".join(dim.anchors_negative),
            scale_min=scale_min,
            scale_max=scale_max,
            mid=mid,
        )
        user = f"候选人面试记录：\n{format_turns(turns)}\n\n请输出该维度的评估 JSON。"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        analysis = self.llm.chat_structured(messages, DimensionAnalysis, temperature=0.0)

        return DimensionResult(
            dimension_key=dim.key,
            name=dim.name,
            score=_clamp(analysis.score, scale_min, scale_max),
            confidence=_clamp(analysis.confidence, 0.0, 1.0),
            evidence=analysis.evidence,
            rationale=analysis.rationale,
        )
