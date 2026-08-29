from __future__ import annotations

from app.config import Settings, get_settings
from app.images.base import ImageProvider
from app.images.minimax_svg import MiniMaxSvgProvider
from app.images.registry import ALL_PROMPTS, image_url
from app.images.stub import StubImageProvider


def get_image_provider(settings: Settings | None = None) -> ImageProvider:
    """Return a FREE image provider.

    Uses MiniMax M3 (:free) to generate SVG avatars/scenes when an OpenRouter
    key is set, otherwise the offline SVG stub. No paid raster image models
    are ever used.
    """
    settings = settings or get_settings()
    if settings.image_enabled and settings.openrouter_api_key:
        return MiniMaxSvgProvider(settings)
    return StubImageProvider()