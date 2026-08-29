#!/usr/bin/env python3
"""Pre-generate all avatar + scene images into the static cache.

Run once to generate every image used by the UI so they load instantly at
runtime with ZERO API calls. Idempotent: skips images already cached.

Usage:
  python pregen_images.py            # generate all, skip existing
  python pregen_images.py --force    # regenerate everything
"""
from __future__ import annotations

import argparse

from app.config import get_settings
from app.images import get_image_provider

# Avatar prompts (kept in sync with frontend/src/components/Avatar.jsx).
AVATARS = {
    "judge": "Head-and-shoulders portrait of a dignified Sri Lankan judge in a black judicial robe and white neck band, seated at a raised wooden bench, warm courtroom lighting, elegant painted portrait illustration",
    "prosecution": "Head-and-shoulders portrait of a confident Sri Lankan state prosecutor in a dark legal suit with white collar, holding a case file, courtroom painted portrait illustration",
    "defense": "Head-and-shoulders portrait of a composed Sri Lankan defense lawyer in a dark legal suit with white collar, courtroom painted portrait illustration",
    "witness": "Head-and-shoulders portrait of a Sri Lankan witness giving testimony in plain clothes, standing at a witness stand, courtroom painted portrait illustration",
    "intake": "Head-and-shoulders portrait of a Sri Lankan court clerk holding a stack of case files, courtroom painted portrait illustration",
}

# Scene prompts (kept in sync with frontend/src/components/SceneVisualizer.jsx).
SCENES = {
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Regenerate all images.")
    args = parser.parse_args()

    settings = get_settings()
    provider = get_image_provider(settings)
    print(f"Using provider: {provider.name} (stub={provider.is_stub()})")

    prompts = []
    for key, p in AVATARS.items():
        prompts.append((f"avatar_{key}", p))
    for key, p in SCENES.items():
        prompts.append((f"scene_{key}", p))

    total = len(prompts)
    for i, (name, prompt) in enumerate(prompts, 1):
        print(f"[{i}/{total}] {name} ...", end=" ", flush=True)
        try:
            url = provider.generate(prompt)
            print("OK" if url.startswith("data:image/svg") else "??")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL: {str(exc)[:80]}")

    cache_dir = settings.image_cache_dir
    files = list(cache_dir.glob("*.svg")) if cache_dir.exists() else []
    print(f"\nDone. {len(files)} images cached in {cache_dir}")


if __name__ == "__main__":
    main()