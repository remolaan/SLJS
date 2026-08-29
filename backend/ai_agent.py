#!/usr/bin/env python3
"""Give a free OpenRouter model a coding / design task.

Reads the task from a file, stdin, or --task, sends it to the configured
free model (default z-ai/glm-5.2:free), and prints the reply.

Usage:
  python ai_agent.py "Explain this function: def foo():"
  python ai_agent.py --model minimax/minimax-m3:free "Design a courtroom UI"
  echo "review this code" | python ai_agent.py
  python ai_agent.py --file backend/app/graph/trial.py --task "Refactor: explain it"
"""
from __future__ import annotations

import argparse
import sys

from app.config import get_settings
from app.llm.base import Message
from app.llm.openrouter import OpenRouterProvider
from app.llm.stub import StubProvider


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="", help="The task/prompt.")
    parser.add_argument("--file", default="", help="A file whose content is attached as context.")
    parser.add_argument("--model", default="", help="Override the model (default: dev_model).")
    parser.add_argument("--role", default="senior software engineer", help="System prompt role.")
    args = parser.parse_args()

    settings = get_settings()

    # Build the prompt.
    parts = [args.task] if args.task else []
    if args.file:
        try:
            content = open(args.file, encoding="utf-8").read()
            parts.append(f"\n\n--- FILE: {args.file} ---\n{content[:6000]}")
        except OSError as exc:
            print(f"Error reading {args.file}: {exc}")
            sys.exit(1)

    if not parts:
        # read from stdin
        stdin_data = sys.stdin.read().strip()
        parts = [stdin_data]

    task = "\n".join(parts).strip()
    if not task:
        print("No task given.")
        sys.exit(1)

    model = args.model or settings.dev_model

    if settings.openrouter_api_key:
        llm = OpenRouterProvider(settings)
    else:
        print("No OPENROUTER_API_KEY set — using stub.")
        llm = StubProvider()

    system = (
        f"You are a {args.role} helping on the 'AI Judge' courtroom "
        "simulation project for Sri Lanka. Be concise and actionable. "
        "Return code, explanation, or design as requested. All scenarios "
        "are hypothetical."
    )
    reply = llm.complete(
        [Message("system", system), Message("user", task)],
        model=model,
        temperature=0.3,
    )
    print(f"--- {model} ---")
    print(reply)


if __name__ == "__main__":
    main()