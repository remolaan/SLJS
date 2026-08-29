from __future__ import annotations

from abc import ABC, abstractmethod


class ImageProvider(ABC):
    """Generate an image from a text prompt.

    Returns a data URL (e.g. "data:image/png;base64,..." or an inline SVG
    data URL) so the result is self-contained and easy to display or cache.
    """

    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Return a data URL for the generated image."""

    def is_stub(self) -> bool:
        return False