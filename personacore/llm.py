"""LLM 客户端（OpenAI 兼容接口）。

通过 OPENAI_BASE_URL / OPENAI_API_KEY / LLM_MODEL 指向任意 OpenAI 兼容服务
（OpenAI、DeepSeek、通义千问、智谱等），后续可扩展其他 Provider。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from openai import OpenAI


def extract_json(text: str) -> Any:
    """从模型输出中稳健地提取 JSON 对象/数组。"""
    text = text.strip()
    if not text:
        raise ValueError("模型返回了空内容")

    # 去掉 markdown 代码块
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 回退：截取第一个 { 到最后一个 }（或 [ 到 ]）
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"无法从模型输出解析 JSON：{text[:300]}")


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

        if not self.api_key:
            raise RuntimeError(
                "未配置 API Key：请复制 .env.example 为 .env，并填写 OPENAI_API_KEY "
                "（以及对应的 OPENAI_BASE_URL / LLM_MODEL）。"
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    def chat_json(self, messages: List[Dict[str, str]], temperature: float = 0.0) -> Any:
        return extract_json(self.chat(messages, temperature=temperature))
