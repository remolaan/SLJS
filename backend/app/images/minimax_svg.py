from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.config import Settings
from app.images.base import ImageProvider
from app.llm.base import Message
from app.llm.openrouter import OpenRouterProvider
from app.llm.stub import StubProvider

_SVG_RE = re.compile(r"<svg.*?</svg>", re.S)


class MiniMaxSvgProvider(ImageProvider):
    """FREE image generation via MiniMax M3 (:free) producing SVG.

    MiniMax M3 is free on OpenRouter but only outputs text, so we ask it to
    emit SVG code and return it as a data URL. This avoids the paid raster
    image models entirely. If no OpenRouter key is configured, falls back to
    the deterministic SVG stub.

    Generated images are cached to disk keyed by a hash of the prompt, so the
    same avatar/scene is generated ONCE and served instantly afterwards (this
    avoids re-burning the free daily quota and makes images load reliably).
    """

    name = "minimax-svg"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._models = settings.free_models or [settings.image_model]
        self._cache_dir: Path = settings.image_cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _llm_for(self, model: str):
        # Always build a fresh provider so each model attempt uses its own client.
        if self._settings.openrouter_api_key:
            llm = OpenRouterProvider(self._settings)
            return llm, model
        return StubProvider(), model

    def generate(self, prompt: str, **kwargs: Any) -> str:
        key = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:24]
        cache_path = self._cache_dir / f"{key}.svg"

        # Cache hit: serve instantly without any model call.
        if cache_path.exists():
            svg = cache_path.read_text(encoding="utf-8")
            return "data:image/svg+xml," + quote(svg)

        # Cache miss: try each free model in turn until one returns SVG.
        last_err = "no model produced an image"
        for model in self._models:
            llm, _ = self._llm_for(model)
            try:
                svg = llm.complete(
                    [
                        Message(
                            "system",
                            "You are a vector illustration generator. Output ONLY valid "
                            "SVG between <svg> and </svg>. No markdown, no code fences, "
                            "no explanations, no HTML. Use clean flat colors and simple "
                            "shapes suitable for an avatar or scene. All subjects are "
                            "illustrative, not real people.",
                        ),
                        Message("user", prompt),
                    ],
                    model=model,
                    temperature=kwargs.get("temperature", 0.6),
                )
                m = _SVG_RE.search(svg)
                if m:
                    body = m.group(0)
                    try:
                        cache_path.write_text(body, encoding="utf-8")
                    except OSError:  # noqa: BLE001 - caching is best-effort
                        pass
                    return "data:image/svg+xml," + quote(body)
                last_err = "model returned no valid SVG"
            except Exception as exc:  # noqa: BLE001 - try next model
                last_err = str(exc)[:120]
        raise ValueError(f"All free models failed: {last_err}")