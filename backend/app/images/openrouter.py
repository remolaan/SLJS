from __future__ import annotations

import base64
import re
from typing import Any

from openai import OpenAI

from app.config import Settings
from app.images.base import ImageProvider


class OpenRouterImageProvider(ImageProvider):
    """Generate images via an OpenRouter image-output model.

    Uses the OpenAI-compatible chat/completions endpoint. The chosen model
    (e.g. google/gemini-3.1-flash-image) returns the image in the message
    content, which we convert to a data URL.
    """

    name = "openrouter"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    def generate(self, prompt: str, **kwargs: Any) -> str:
        model = kwargs.get("model", self._settings.image_model)
        resp = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        message = resp.choices[0].message
        return _extract_image_data_url(message, prompt)


def _extract_image_data_url(message, prompt: str) -> str:
    """Pull an image (data URL) out of a chat-completions response.

    OpenRouter image models return the image in several possible places:
      - message.images -> list of {"type":"image_url","image_url":{"url": ...}}
      - message.content as a JSON string with an "inline_data" base64 field
      - message.content as a list of parts with image_url
    """
    # Case 1: message.images (primary, most reliable).
    images = getattr(message, "images", None)
    if images:
        for part in images:
            if isinstance(part, dict):
                url = part.get("image_url")
                if isinstance(url, dict):
                    url = url.get("url", "")
                if isinstance(url, str) and url.startswith("data:image"):
                    return url

    content = getattr(message, "content", None)
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "image_url":
                url = part.get("image_url")
                if isinstance(url, dict):
                    url = url.get("url", "")
                if url:
                    return url
            if part.get("type") == "output_text" and part.get("text"):
                found = _try_parse_inner(part["text"])
                if found:
                    return found

    if isinstance(content, str):
        found = _try_parse_inner(content)
        if found:
            return found

    raise ValueError("No image found in model response")


def _try_parse_inner(text: str) -> str | None:
    # Already a data URL?
    m = re.search(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+", text)
    if m:
        return m.group(0)

    # Gemini-style JSON with inline_data: {"data": "<base64>", "mime_type": ...}
    m = re.search(r'"inline_data"\s*:\s*\{[^}]*"data"\s*:\s*"([^"]+)"[^}]*"mime_type"\s*:\s*"([^"]+)"', text)
    if m:
        b64, mime = m.group(1), m.group(2)
        mime = mime if mime.startswith("image/") else "image/png"
        return f"data:{mime};base64,{b64}"

    # Try to find a JSON blob containing base64 image data.
    m = re.search(r'"image(?:_url)?"\s*:\s*"([^"]+)"', text)
    if m:
        payload = m.group(1)
        if payload.startswith("data:"):
            return payload
        if payload.startswith("http"):
            return payload
        # assume raw base64
        try:
            base64.b64decode(payload, validate=True)
            return "data:image/png;base64," + payload
        except Exception:  # noqa: BLE001
            pass

    # Plain base64 in the whole text.
    stripped = text.strip()
    if len(stripped) > 100:
        try:
            base64.b64decode(stripped, validate=True)
            return "data:image/png;base64," + stripped
        except Exception:  # noqa: BLE001
            pass
    return None