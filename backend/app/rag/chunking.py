from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

# A chunk carries a stable id, its source file, a human-readable cite, a
# doc_type ("statute" | "precedent" | "constitution") and the text.


class Chunk:
    __slots__ = ("chunk_id", "doc_type", "source", "cite", "text")

    def __init__(
        self,
        chunk_id: str,
        doc_type: str,
        source: str,
        cite: str,
        text: str,
    ):
        self.chunk_id = chunk_id
        self.doc_type = doc_type
        self.source = source
        self.cite = cite
        self.text = text

    def as_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_type": self.doc_type,
            "source": self.source,
            "cite": self.cite,
            "text": self.text,
        }


# --- structure-aware chunking -------------------------------------------------


def chunk_statute(text: str, filename: str, source_title: str) -> list[Chunk]:
    """Split a statute file by sections (s.XX) rather than fixed windows."""
    # Normalise the statute preamble/act heading.
    lines = text.splitlines()
    preamble = _preamble(lines)
    chunks: list[Chunk] = []

    # Split on section headings like "s.324" / "Section 324" / "324." at line start.
    pattern = re.compile(r"^\s*(?:s(?:ection)?\.?\s*|Section\s+)(\d+)\s*[.:-]", re.I)
    current_sec: str | None = None
    current_lines: list[str] = []

    def flush():
        nonlocal current_lines
        if current_sec and current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                cite = f"{source_title}, s.{current_sec}"
                chunks.append(
                    Chunk(
                        chunk_id=f"{filename}::s{current_sec}",
                        doc_type="statute",
                        source=filename,
                        cite=cite,
                        text=f"{cite}\n{body}",
                    )
                )
        current_lines = []

    for line in lines:
        m = pattern.match(line)
        if m:
            flush()
            current_sec = m.group(1)
            current_lines = [line]
        else:
            current_lines.append(line)
    flush()

    if not chunks:
        # Fall back to whole document if no sections were detected.
        chunks.append(
            Chunk(
                chunk_id=f"{filename}::whole",
                doc_type="statute",
                source=filename,
                cite=source_title,
                text="\n".join(lines).strip(),
            )
        )
    return chunks


def _preamble(lines: list[str]) -> str:
    head = [l for l in lines[:12] if l.strip()][:6]
    return "\n".join(head)


def chunk_judgment(text: str, filename: str, case_name: str) -> list[Chunk]:
    """Split a judgment by semantic headers: Facts / Issues / Reasoning / Held."""
    markers = [
        (r"^\s*(?:Facts|FACT|The Facts|Background)\b", "Facts"),
        (r"^\s*(?:Issues|ISSUES|Questions? for determination)\b", "Issues"),
        (r"^\s*(?:Reasoning|Consideration|Analysis|Discussion)\b", "Reasoning"),
        (r"^\s*(?:Held|HELD|Decision|Conclusion|Order)\b", "Held"),
    ]
    compiled = [(re.compile(p), name) for p, name in markers]

    lines = text.splitlines()
    chunks: list[Chunk] = []
    current: tuple[str, list[str]] | None = None

    def flush():
        nonlocal current
        if current:
            label, body = current
            body_text = "\n".join(body).strip()
            if body_text:
                cite = f"{case_name}"
                chunks.append(
                    Chunk(
                        chunk_id=f"{filename}::{label.lower()}",
                        doc_type="precedent",
                        source=filename,
                        cite=cite,
                        text=f"{cite} [{label}]\n{body_text}",
                    )
                )

    for line in lines:
        matched = None
        for pat, name in compiled:
            if pat.match(line):
                matched = name
                break
        if matched:
            flush()
            current = (matched, [line])
        else:
            if current is None:
                # Header material before first section belongs to the case intro.
                current = ("Case", [line])
            else:
                current[1].append(line)
    flush()
    return chunks


def chunk_document(path: Path) -> list[Chunk]:
    """Route a corpus file to the right chunker based on its doc-type tag."""
    text = path.read_text(encoding="utf-8", errors="replace")
    head = text[:600].lower()

    if "type: precedent" in head or "/judgments/" in str(path):
        case_name = path.stem.replace("_", " ")
        return chunk_judgment(text, path.name, case_name)

    if "type: constitution" in head:
        return _chunk_articles(text, path.name, "Constitution of Sri Lanka")

    # Default: statute by section.
    source_title = path.stem.replace("_", " ").title()
    return chunk_statute(text, path.name, source_title)


def _chunk_articles(text: str, filename: str, title: str) -> list[Chunk]:
    """Constitution: chunk by Article N (Roman numerals in the real doc)."""
    pattern = re.compile(r"^\s*(?:Article|ART|Art)\s+(\w+)\b", re.I)
    chunks: list[Chunk] = []
    current: tuple[str, list[str]] | None = None

    def flush():
        nonlocal current
        if current:
            art, body = current
            body_text = "\n".join(body).strip()
            if body_text:
                chunks.append(
                    Chunk(
                        chunk_id=f"{filename}::art{art}",
                        doc_type="constitution",
                        source=filename,
                        cite=f"{title}, Art. {art}",
                        text=f"{title}, Art. {art}\n{body_text}",
                    )
                )

    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            flush()
            current = (m.group(1), [line])
        elif current is not None:
            current[1].append(line)
    flush()

    if not chunks:
        chunks.append(
            Chunk(
                chunk_id=f"{filename}::whole",
                doc_type="constitution",
                source=filename,
                cite=title,
                text=text.strip(),
            )
        )
    return chunks


def load_corpus(corpus_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    if not corpus_dir.exists():
        return chunks
    for path in sorted(corpus_dir.rglob("*.txt")):
        chunks.extend(chunk_document(path))
    return chunks