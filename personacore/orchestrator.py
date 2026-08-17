"""编排器：CLI 交互循环，驱动 InterviewEngine 完成面试与报告。"""
from __future__ import annotations

from typing import Callable

from .config import AppConfig
from .engine import InterviewEngine
from .llm import LLMClient
from .session import RunResult


class Orchestrator:
    def __init__(self, config: AppConfig, llm: LLMClient):
        self.config = config
        self.llm = llm

    def run(
        self,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> RunResult:
        """执行一次完整测评（命令行交互），返回 RunResult。"""
        engine = InterviewEngine(self.config, self.llm)
        opening, first_q = engine.start()
        output_fn(opening)
        output_fn(f"[面试官] {first_q}")

        while not engine.finished:
            answer = input_fn("你 > ")
            reply = engine.send(answer)
            output_fn(f"[面试官] {reply}")

        output_fn("\n（正在分析并生成报告……）")
        return engine.finalize()
