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


def _balanced_end(text: str, start: int, opener: str, closer: str) -> int:
    """从 start 开始找与 opener 匹配的 closer 位置（尊重字符串与转义）。"""
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return i
    return -1


def extract_json(text: str) -> Any:
    """从模型输出中稳健地提取 JSON 对象/数组（容错：代码块、尾随文本、尾随逗号）。"""
    text = text.strip()
    if not text:
        raise ValueError("模型返回了空内容")

    # 去掉 markdown 代码块
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    candidates = [text]
    # 从第一个 {/[ 开始截取平衡片段，忽略尾随的说明文字
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start != -1:
            end = _balanced_end(text, start, opener, closer)
            if end != -1:
                candidates.append(text[start : end + 1])

    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            # 修复常见问题：尾随逗号
            fixed = re.sub(r",\s*([}\]])", r"\1", cand)
            try:
                return json.loads(fixed)
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
        # 优先用 JSON 模式强制合法 JSON（DeepSeek/OpenAI 支持）；供应商不支持则回退
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            text = (resp.choices[0].message.content or "").strip()
        except Exception:
            text = self.chat(messages, temperature=temperature)
        return extract_json(text)
