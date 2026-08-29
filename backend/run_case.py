#!/usr/bin/env python3
"""Run a full AI trial end-to-end and print the transcript + judgment.

Usage:
    python run_case.py [--seed market_altercation|shophouse_theft] [--json]

Without a provider API key configured, the pipeline runs on the built-in
stub provider so the state machine, RAG wiring and output shape can be
verified offline.
"""
from __future__ import annotations

import argparse
import json
import logging

from app.config import get_settings
from app.graph.trial import run_trial
from app.rag.store import get_vectorstore
from app.seed.cases import SEED_CASES

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", choices=list(SEED_CASES.keys()), default="market_altercation")
    parser.add_argument("--json", action="store_true", help="Emit result as JSON.")
    parser.add_argument("--no-witness", action="store_true", help="Skip the witness round.")
    args = parser.parse_args()

    settings = get_settings()
    print(f"LLM provider: {settings.effective_provider}")

    store = get_vectorstore(settings)
    print(f"Vector store chunks: {store.count()}")

    case = SEED_CASES[args.seed]()
    result = run_trial(
        case,
        settings=settings,
        include_witness=not args.no_witness,
    )

    if args.json:
        print(json.dumps(result.model_dump(), indent=2, default=str))
        return

    print("\n" + "=" * 70)
    print(f"COURTROOM TRANSCRIPT — {result.case_title}")
    print("=" * 70)
    for turn in result.transcript:
        head = f"[{turn.label or turn.role}]"
        print(f"\n--- {head} ---")
        print(turn.content)

    print("\n" + "=" * 70)
    print("RETRIEVED LAW (RAG)")
    print("=" * 70)
    for ctx in result.retrieved_context:
        print(f"\n[{ctx.source}][rel {ctx.relevance}] {ctx.text[:300]}")

    print("\n" + "=" * 70)
    print("STRUCTURED JUDGMENT")
    print("=" * 70)
    j = result.judgment
    if j:
        print(f"VERDICT: {j.verdict}")
        print(f"Facts found:\n{j.facts_found}")
        print(f"Legal reasoning:\n{j.legal_reasoning}")
        print(f"Citations: {j.citations}")
        if j.sentence:
            print(f"Sentence: {j.sentence.model_dump()}")
        print(f"Release: {j.release}")
        print(f"Dissent notes: {j.dissent_notes or '(none)'}")


if __name__ == "__main__":
    main()