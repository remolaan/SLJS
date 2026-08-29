from __future__ import annotations

from app.llm.base import LLMProvider, Message


class Agent:
    """Base class: a single LLM call with a fixed role system prompt.

    Each agent = a distinct model call with its own constraints, keeping
    reasoning separable and auditable per the project brief.
    """

    role: str = "agent"
    system_prompt: str = "You are a courtroom simulation agent."

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, user: str, **kwargs) -> str:
        return self.llm.complete(
            [Message("system", self.system_prompt), Message("user", user)],
            **kwargs,
        )