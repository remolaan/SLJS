from __future__ import annotations


from app.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.llm.openrouter import OpenRouterProvider
from app.llm.stub import StubProvider


def get_llm(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider = settings.effective_provider
    if provider == "deepseek":
        return DeepSeekProvider(settings)
    if provider in ("openrouter", "minimax"):
        return OpenRouterProvider(settings)
    return StubProvider()