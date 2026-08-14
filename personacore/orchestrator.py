"""编排器：串起「面试 → 维度分析 → 裁决 → 报告」完整流程。"""
from __future__ import annotations

from typing import Callable, Dict, List

from .agents.analyst import Analyst, DimensionResult
from .agents.arbiter import Arbiter
from .agents.interviewer import Interviewer
from .config import AppConfig, Dimension
from .llm import LLMClient
from .session import RunResult, make_run_id, make_timestamp


class Orchestrator:
    def __init__(self, config: AppConfig, llm: LLMClient):
        self.config = config
        self.llm = llm
        self.interviewer = Interviewer(llm)
        self.analyst = Analyst(llm)
        self.arbiter = Arbiter(llm)

    def run(
        self,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> RunResult:
        """执行一次完整测评，返回包含面试记录与分析的 RunResult。"""
        run_id = make_run_id()
        started_at = make_timestamp()
        output_fn(self.interviewer.opening())

        transcripts: Dict[str, List[Dict[str, str]]] = {}
        for dim in self.config.dimensions:
            transcripts[dim.key] = self._interview_dimension(dim, input_fn, output_fn)

        output_fn(self.interviewer.closing())
        output_fn("\n（正在分析并生成报告……）")

        results: List[DimensionResult] = [
            self.analyst.analyze(
                dim, transcripts[dim.key], self.config.scale_min, self.config.scale_max
            )
            for dim in self.config.dimensions
        ]
        arb = self.arbiter.arbitrate(results, self.config)

        return RunResult(
            run_id=run_id,
            started_at=started_at,
            model=self.llm.model,
            config=self.config,
            transcripts=transcripts,
            dimension_results=results,
            arbiter=arb,
        )

    def _interview_dimension(
        self,
        dim: Dimension,
        input_fn: Callable[[str], str],
        output_fn: Callable[[str], None],
    ) -> List[Dict[str, str]]:
        question = dim.questions[0]
        output_fn(f"\n[面试官] {question}")
        answer = input_fn("你 > ")
        turns: List[Dict[str, str]] = [
            {"role": "interviewer", "content": question},
            {"role": "candidate", "content": answer},
        ]

        for _ in range(self.config.max_probes):
            followup = self.interviewer.decide_followup(dim, turns)
            if followup.strip().upper() == "DONE":
                break
            output_fn(f"\n[面试官] {followup}")
            answer = input_fn("你 > ")
            turns.append({"role": "interviewer", "content": followup})
            turns.append({"role": "candidate", "content": answer})

        return turns
