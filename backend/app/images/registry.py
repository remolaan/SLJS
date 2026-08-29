from __future__ import annotations

import hashlib
from pathlib import Path


def cache_key(prompt: str) -> str:
    """Hash a prompt to its cached SVG filename stem."""
    return hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:24]


# The canonical set of pre-generated images (name -> prompt).
# Must match pregen_images.py.
AVATAR_PROMPTS = {
    "judge": "Head-and-shoulders portrait of a dignified Sri Lankan judge in a black judicial robe and white neck band, seated at a raised wooden bench, warm courtroom lighting, elegant painted portrait illustration",
    "prosecution": "Head-and-shoulders portrait of a confident Sri Lankan state prosecutor in a dark legal suit with white collar, holding a case file, courtroom painted portrait illustration",
    "defense": "Head-and-shoulders portrait of a composed Sri Lankan defense lawyer in a dark legal suit with white collar, courtroom painted portrait illustration",
    "witness": "Head-and-shoulders portrait of a Sri Lankan witness giving testimony in plain clothes, standing at a witness stand, courtroom painted portrait illustration",
    "intake": "Head-and-shoulders portrait of a Sri Lankan court clerk holding a stack of case files, courtroom painted portrait illustration",
}

SCENE_PROMPTS = {
    "case_intake": "A court clerk arranging case files at the registry desk in a Sri Lankan courthouse",
    "prosecution_opening": "A Sri Lankan prosecutor standing at the prosecution table, opening the case before the judge",
    "defense_response": "A Sri Lankan defense lawyer standing at the defense table responding to the prosecution",
    "prosecution_evidence": "The prosecutor presenting a bundle of documents and physical evidence to the court",
    "witness_testimony": "A witness standing in the witness box giving testimony before the judge",
    "defense_evidence": "The defense counsel presenting evidence and character references",
    "prosecution_closing": "The prosecutor delivering a passionate closing argument to the bench",
    "defense_closing": "The defense counsel delivering a final closing plea to the bench",
    "law_retrieval": "The judge reviewing law books and case reports on the bench, referencing statutes",
    "judgment": "The judge seated at the high bench reading the final judgment, holding a gavel",
    "deliberation": "The judge seated alone at the bench writing the judgment",
}

ALL_PROMPTS = {**{f"avatar_{k}": v for k, v in AVATAR_PROMPTS.items()}, **SCENE_PROMPTS}


def image_url(name: str, cache_dir: Path) -> str | None:
    """Return the static URL for a named pre-generated image, or None.

    Accepts both the raw key (e.g. 'judgment') and the frontend's
    'scene_'/'avatar_' prefixed aliases (e.g. 'scene_judgment').
    """
    lookup = name
    if name.startswith('scene_'):
        lookup = name[len('scene_'):]
    prompt = ALL_PROMPTS.get(lookup)
    if not prompt:
        return None
    key = cache_key(prompt)
    if (cache_dir / f"{key}.svg").exists():
        return f"/static/images/{key}.svg"
    return None