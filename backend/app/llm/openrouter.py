from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.config import Settings
from app.llm.base import LLMProvider, Message


class OpenRouterProvider(LLMProvider):
    """Any OpenRouter model via the OpenAI-compatible chat API.

    Used here for MiniMax M3 (free tier: minimax/minimax-m3:free) to help
    design UI copy/prompts. The model is configurable so the same provider
    can drive other OpenRouter models too.
    """

    name = "openrouter"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    def complete(self, messages: list[Message], **kwargs: Any) -> str:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        models = kwargs.get("model")
        if models:
            models = [models]
        else:
            # Default to the UI model, falling back to other free models.
            models = [self._settings.ui_model] + [
                m for m in self._settings.free_models if m != self._settings.ui_model
            ]

        last_err = "no model responded"
        for model in models:
            try:
                resp = self._client.chat.completions.create(
                    model=model,
                    messages=payload,
                    temperature=kwargs.get("temperature", 0.7),
                    extra_body={"extra_headers": {"HTTP-Referer": "http://localhost:5173"}},
                )
                content = resp.choices[0].message.content or ""
                if content.strip():
                    return content
                last_err = "empty response"
            except Exception as exc:  # noqa: BLE001 - try next free model on rate limit
                last_err = str(exc)[:120]
        raise RuntimeError(f"All free models failed: {last_err}")