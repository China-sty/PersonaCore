"""智能体结构化输出的 Pydantic 模型（LLM 输出契约）。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FollowupDecision(BaseModel):
    """面试官追问判断。"""
    done: bool = Field(description="候选人回答是否已包含足够的行为证据")
    question: str = Field(description="追问内容；done 为 true 时为空字符串")


class DimensionAnalysis(BaseModel):
    """维度分析结果（原始 LLM 输出）。"""
    score: float = Field(description="该维度得分")
    confidence: float = Field(description="置信度，0~1")
    evidence: list[str] = Field(description="候选人回答原文中的证据引用")
    rationale: str = Field(description="一句话评分理由")
