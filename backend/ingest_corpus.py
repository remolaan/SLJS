#!/usr/bin/env python3
"""Ingest the legal corpus into the Chroma vector store.

Usage:
    python ingest_corpus.py [--force]

Drops chunks into backend/data/vectorstore. Idempotent by default
(re-ingesting skips already-present chunk ids). --force rebuilds.
"""
from __future__ import annotations

import argparse
import logging

from app.config import get_settings
from app.rag.store import get_vectorstore

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Re-add all chunks.")
    args = parser.parse_args()

    settings = get_settings()
    store = get_vectorstore(settings)
    added = store.sync_corpus(force=args.force)
    print(f"Vector store now holds {store.count()} chunks ({added} added).")


if __name__ == "__main__":
    main()