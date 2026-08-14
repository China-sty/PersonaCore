"""报告 Agent：将裁决结果渲染为结构化 Markdown 报告。"""
from __future__ import annotations

from typing import List

from ..config import AppConfig
from .arbiter import ArbiterResult


class Reporter:
    def render(self, arb: ArbiterResult, config: AppConfig) -> str:
        lines: List[str] = []
        lines.append("## 综合结论")
        lines.append("")
        lines.append(
            f"**综合得分**：{arb.composite:.2f} / {config.scale_max}　|　"
            f"**结论**：{arb.decision}"
        )
        lines.append("")
        lines.append("## 各维度得分")
        lines.append("")
        lines.append("| 维度 | 得分 | 置信度 | 合格线 | 是否达标 |")
        lines.append("|------|------|--------|--------|----------|")
        for v in arb.verdicts:
            mark = "达标" if v.passed else "未达标"
            lines.append(
                f"| {v.name} | {v.score:.1f} | {v.confidence:.0%} | {v.threshold:.1f} | {mark} |"
            )
        lines.append("")
        lines.append("## 证据与理由")
        lines.append("")
        for v in arb.verdicts:
            lines.append(f"### {v.name}")
            lines.append(f"- **理由**：{v.rationale}")
            for e in v.evidence:
                lines.append(f"- **证据**：“{e}”")
            lines.append("")
        lines.append("## 总体评价")
        lines.append("")
        lines.append(arb.summary)
        lines.append("")
        if arb.flags:
            lines.append("## 提示")
            lines.append("")
            for f in arb.flags:
                lines.append(f"- {f}")
            lines.append("")
        lines.append("> 本报告由多智能体系统生成，仅作为招聘辅助参考，最终判断由人工完成。")
        return "\n".join(lines)
