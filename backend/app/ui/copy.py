from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.base import Message
from app.llm.openrouter import OpenRouterProvider
from app.llm.stub import StubProvider


def generate_design_copy(prompt: str, settings: Settings | None = None) -> dict:
    """Use MiniMax M3 (OpenRouter) to draft courtroom UI copy / scene prompts.

    Falls back to the stub provider if no OpenRouter key is configured, so
    the endpoint is always usable.
    """
    settings = settings or get_settings()
    if settings.openrouter_api_key:
        llm = OpenRouterProvider(settings)
        model = settings.ui_model
    else:
        llm = StubProvider()
        model = "stub"
    system = (
        "You are a UI/UX copywriter for an AI courtroom simulation web app "
        "for Sri Lanka. Return concise, professional courtroom-themed text "
        "or JSON as requested. All scenarios are hypothetical."
    )
    reply = llm.complete(
        [Message("system", system), Message("user", prompt)], temperature=0.7
    )
    return {
        "provider": llm.name,
        "model": model,
        "copy": reply,
    }