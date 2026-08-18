"""测评会话结果：保存每次运行的全链路数据（面试记录 + 分析），并渲染为报告。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from .agents.analyst import DimensionResult
from .agents.arbiter import ArbiterResult
from .agents.report import Reporter
from .config import AppConfig


def make_run_id() -> str:
    """生成一次运行的唯一 ID（时间戳到毫秒）。"""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


def make_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class RunResult:
    run_id: str
    started_at: str
    model: str
    config: AppConfig
    transcripts: Dict[str, List[Dict[str, str]]]
    dimension_results: List[DimensionResult]
    arbiter: ArbiterResult

    def full_markdown(self) -> str:
        """完整报告：元信息 + 面试全记录 + 最终分析。"""
        parts: List[str] = []
        parts.append("# PersonaCore 测评报告（大五人格）")
        parts.append("")
        parts.append(f"- **Run ID**：{self.run_id}")
        parts.append(f"- **时间**：{self.started_at}")
        parts.append(f"- **模型**：{self.model}")
        parts.append("")
        parts.append("## 面试全记录")
        parts.append("")
        for dim in self.config.dimensions:
            parts.append(f"### {dim.name}")
            for t in self.transcripts.get(dim.key, []):
                role = "面试官" if t["role"] == "interviewer" else "候选人"
                line = f"- **{role}**：{t['content']}"
                sig = t.get("signals")
                if isinstance(sig, dict) and sig.get("emotion"):
                    conf = sig.get("confidence")
                    suffix = f"（置信度 {conf:.2f}）" if isinstance(conf, (int, float)) else ""
                    line += f"　*语音情绪：{sig['emotion']}{suffix}*"
                parts.append(line)
            parts.append("")
        parts.append(Reporter().render(self.arbiter, self.config))
        return "\n".join(parts)

    def to_dict(self) -> dict:
        """结构化数据，供程序化分析 / 入库 / 下游系统消费。"""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "model": self.model,
            "transcript": self.transcripts,
            "dimensions": [
                {
                    "key": r.dimension_key,
                    "name": r.name,
                    "score": r.score,
                    "confidence": r.confidence,
                    "evidence": r.evidence,
                    "rationale": r.rationale,
                }
                for r in self.dimension_results
            ],
            "verdicts": [
                {
                    "key": v.dimension_key,
                    "name": v.name,
                    "score": v.score,
                    "threshold": v.threshold,
                    "weight": v.weight,
                    "passed": v.passed,
                }
                for v in self.arbiter.verdicts
            ],
            "composite": self.arbiter.composite,
            "decision": self.arbiter.decision,
            "flags": self.arbiter.flags,
            "summary": self.arbiter.summary,
        }
