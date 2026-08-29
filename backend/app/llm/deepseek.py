from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.config import Settings
from app.llm.base import LLMProvider, Message


class DeepSeekProvider(LLMProvider):
    """DeepSeek via the OpenAI-compatible chat API."""

    name = "deepseek"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    def complete(self, messages: list[Message], **kwargs: Any) -> str:
        payload = [
            {"role": m.role, "content": m.content} for m in messages
        ]
        resp = self._client.chat.completions.create(
            model=kwargs.get("model", self._settings.deepseek_model),
            messages=payload,
            temperature=kwargs.get(
                "temperature", self._settings.deepseek_temperature
            ),
        )
        return resp.choices[0].message.content or ""