"""面试状态机：无 I/O 的面试核心，供 CLI 与 Web 层复用。"""
from __future__ import annotations

import threading
from typing import Dict, List

from .agents.analyst import Analyst
from .agents.arbiter import Arbiter
from .agents.interviewer import Interviewer
from .config import AppConfig
from .llm import LLMClient
from .session import RunResult, make_run_id, make_timestamp


class InterviewEngine:
    """驱动一次完整面试的状态机，每次 `send()` 推进一个对话回合。"""

    def __init__(self, config: AppConfig, llm: LLMClient):
        self.config = config
        self.llm = llm
        self.interviewer = Interviewer(llm)
        self.analyst = Analyst(llm)
        self.arbiter = Arbiter(llm)
        self.dims = list(config.dimensions)
        self.transcripts: Dict[str, List[Dict[str, str]]] = {}
        self._i = 0                                  # 当前维度下标
        self._turns: List[Dict[str, str]] = []        # 当前维度进行中的问答
        self._probes = 0
        self.finished = False
        self._result: RunResult | None = None
        self._finalize_lock = threading.Lock()

    def start(self) -> List[str]:
        """返回 [开场白, 第一个问题]。"""
        opening = self.interviewer.opening()
        q = self.dims[0].questions[0]
        self._turns = [{"role": "interviewer", "content": q}]
        return [opening, q]

    def send(self, answer: str, signals: dict | None = None) -> str:
        """候选人回答后，返回面试官下一条消息；面试结束时返回结束语并置 finished。

        signals 为可选的语音信号 dict（如 {"emotion":"平静","confidence":0.9}），
        会作为辅助证据注入分析师/面试官的上下文。
        """
        if self.finished:
            raise RuntimeError("面试已结束")

        dim = self.dims[self._i]
        turn: dict = {"role": "candidate", "content": answer}
        if signals:
            turn["signals"] = signals
        self._turns.append(turn)

        # 判断是否需要追问
        if self._probes < self.config.max_probes:
            followup = self.interviewer.decide_followup(dim, self._turns)
            if followup.strip().upper() != "DONE":
                self._probes += 1
                self._turns.append({"role": "interviewer", "content": followup})
                return followup

        # 当前维度完成，进入下一维度
        self.transcripts[dim.key] = self._turns
        self._i += 1
        if self._i < len(self.dims):
            nxt = self.dims[self._i]
            q = nxt.questions[0]
            self._turns = [{"role": "interviewer", "content": q}]
            self._probes = 0
            return q

        self.finished = True
        return self.interviewer.closing()

    def finalize(self) -> RunResult:
        """运行分析 + 裁决，返回 RunResult（可重复调用，结果缓存，线程安全）。"""
        with self._finalize_lock:
            if self._result is not None:
                return self._result
            results = [
                self.analyst.analyze(
                    dim, self.transcripts[dim.key], self.config.scale_min, self.config.scale_max
                )
                for dim in self.dims
            ]
            arb = self.arbiter.arbitrate(results, self.config)
            self._result = RunResult(
                run_id=make_run_id(),
                started_at=make_timestamp(),
                model=self.llm.model,
                config=self.config,
                transcripts=self.transcripts,
                dimension_results=results,
                arbiter=arb,
            )
            return self._result
