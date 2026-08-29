from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Message:
    """A single chat message."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class LLMProvider(ABC):
    """Minimal chat interface shared by every agent.

    Agents talk to this interface rather than a vendor SDK so the model
    is swappable (DeepSeek now, others later) without touching agent code.
    """

    name: str = "base"

    @abstractmethod
    def complete(self, messages: list[Message], **kwargs: Any) -> str:
        """Return the assistant reply for the given chat history."""

    def invoke(self, system: str, user: str, **kwargs: Any) -> str:
        return self.complete(
            [Message("system", system), Message("user", user)], **kwargs
        )