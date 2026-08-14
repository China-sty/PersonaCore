"""裁决 Agent：融合各维度结果，计算综合分，判定筛选结论，并做一致性校验。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..config import AppConfig
from ..llm import LLMClient
from .analyst import DimensionResult

_SUMMARY_SYSTEM = """你是测评主审。根据各维度打分，给出一段 2~3 句的总体评价（中文），客观、克制，
重点说明候选人的优势与需要关注的方面。只输出总体评价，不要输出其他内容。"""


@dataclass
class DimensionVerdict:
    dimension_key: str
    name: str
    score: float
    confidence: float
    evidence: List[str]
    rationale: str
    weight: float
    threshold: float
    veto: bool
    passed: bool


@dataclass
class ArbiterResult:
    verdicts: List[DimensionVerdict]
    composite: float
    decision: str
    flags: List[str] = field(default_factory=list)
    summary: str = ""


class Arbiter:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def arbitrate(self, results: List[DimensionResult], config: AppConfig) -> ArbiterResult:
        dims = {d.key: d for d in config.dimensions}

        verdicts: List[DimensionVerdict] = []
        weighted_sum = 0.0
        for r in results:
            dim = dims[r.dimension_key]
            passed = r.score >= dim.threshold
            verdicts.append(
                DimensionVerdict(
                    dimension_key=r.dimension_key,
                    name=r.name,
                    score=r.score,
                    confidence=r.confidence,
                    evidence=r.evidence,
                    rationale=r.rationale,
                    weight=dim.weight,
                    threshold=dim.threshold,
                    veto=dim.veto,
                    passed=passed,
                )
            )
            weighted_sum += r.score * dim.weight

        composite = weighted_sum / config.total_weight

        # 筛选判定（规则：可配置，当前为 MVP 简化版）
        veto_triggered = [v for v in verdicts if v.veto and not v.passed]
        failed = [v for v in verdicts if not v.passed]
        avg_threshold = sum(d.threshold for d in config.dimensions) / len(config.dimensions)

        if veto_triggered:
            decision = "淘汰"
        elif composite >= avg_threshold and not failed:
            decision = "通过"
        else:
            decision = "待定"

        flags: List[str] = []
        if veto_triggered:
            flags.append("触发一票否决: " + "、".join(v.name for v in veto_triggered))
        if failed:
            flags.append("未达标维度: " + "、".join(v.name for v in failed))
        low_conf = [v for v in verdicts if v.confidence < 0.5]
        if low_conf:
            flags.append("证据不足(低置信度): " + "、".join(v.name for v in low_conf))

        summary = self._summarize(verdicts, composite, decision, config.scale_max)

        return ArbiterResult(
            verdicts=verdicts,
            composite=composite,
            decision=decision,
            flags=flags,
            summary=summary,
        )

    def _summarize(self, verdicts, composite: float, decision: str, scale_max: int) -> str:
        user = (
            "各维度结果：\n"
            + "\n".join(
                f"- {v.name}: {v.score:.1f} (置信度 {v.confidence:.2f})"
                for v in verdicts
            )
            + f"\n综合得分：{composite:.2f}/{scale_max}，结论：{decision}\n\n请给出总体评价。"
        )
        try:
            return self.llm.chat(
                [{"role": "system", "content": _SUMMARY_SYSTEM}, {"role": "user", "content": user}],
                temperature=0.4,
            ).strip()
        except Exception:
            return "（总体评价生成失败，请参考各维度得分。）"
