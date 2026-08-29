from __future__ import annotations

import hashlib
from typing import Any

from app.images.base import ImageProvider


class StubImageProvider(ImageProvider):
    """Offline placeholder that returns a deterministic SVG data URL.

    Lets the frontend render a scene image without any API key. The SVG is a
    simple courtroom-style illustration with the prompt-derived label, and its
    color palette is derived deterministically from the prompt text.
    """

    name = "stub"

    def generate(self, prompt: str, **kwargs: Any) -> str:
        label = _label(prompt)
        hue = int(hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:6], 16) % 360
        light = f"hsl({hue},45%,88%)"
        dark = f"hsl({hue},50%,38%)"
        accent = f"hsl({hue},55%,55%)"

        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='800' height='450' viewBox='0 0 800 450'>
  <defs>
    <linearGradient id='bg' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0%' stop-color='{light}'/>
      <stop offset='100%' stop-color='#f5f0e6'/>
    </linearGradient>
  </defs>
  <rect width='800' height='450' fill='url(#bg)'/>
  <rect x='20' y='20' width='760' height='410' fill='none' stroke='{dark}' stroke-width='3' rx='8'/>
  <rect x='90' y='70' width='300' height='180' fill='#7a2e1d' rx='10'/>
  <rect x='120' y='100' width='80' height='120' fill='#5a1f14'/>
  <rect x='280' y='100' width='80' height='120' fill='#5a1f14'/>
  <rect x='130' y='170' width='240' height='50' fill='#c9a227' rx='4'/>
  <text x='250' y='205' font-family='Georgia' font-size='22' fill='#3b2a00' text-anchor='middle' font-weight='bold'>THE COURT</text>
  <rect x='480' y='90' width='200' height='150' fill='#6b4a2f' rx='8'/>
  <rect x='500' y='110' width='160' height='110' fill='#8a6a45'/>
  <circle cx='620' cy='80' r='26' fill='{accent}'/>
  <text x='580' y='330' font-family='Georgia' font-size='18' fill='{dark}' text-anchor='middle'>PROSECUTION</text>
  <text x='700' y='330' font-family='Georgia' font-size='18' fill='{dark}' text-anchor='middle'>DEFENSE</text>
  <text x='250' y='350' font-family='Georgia' font-size='18' fill='{dark}' text-anchor='middle'>WITNESS</text>
  <text x='400' y='400' font-family='Georgia' font-size='14' fill='{dark}' text-anchor='middle' opacity='0.8'>STUB IMAGE — add OPENROUTER_API_KEY to generate real scenes</text>
  <text x='400' y='60' font-family='Georgia' font-size='16' fill='{dark}' text-anchor='middle'>{label}</text>
</svg>"""
        from urllib.parse import quote

        return "data:image/svg+xml," + quote(svg)

    def is_stub(self) -> bool:
        return True


def _label(prompt: str) -> str:
    label = " ".join(prompt.strip().split())
    if len(label) > 60:
        label = label[:60] + "…"
    return label or "AI Judge"