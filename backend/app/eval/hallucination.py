from __future__ import annotations

import re

from app.models.schemas import CitationCheck, Judgment, RetrievedContext


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation/spacing for citation matching."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _citation_tokens(citation: str) -> str:
    # Focus on the statute/section or case name portion of the citation.
    norm = _normalize(citation)
    # Keep key tokens: statute title + section number, or case name.
    return norm


def check_citations(
    judgment: Judgment | None,
    retrieved_context: list[RetrievedContext],
) -> list[CitationCheck]:
    """Verify each judgment citation appears in the retrieved corpus.

    A citation is 'supported' if its normalized form matches a substring of
    the retrieved statute/precedent text. Otherwise it is flagged as
    unsupported (a possible hallucination).
    """
    if not judgment or not judgment.citations:
        return []

    haystacks = [_normalize(c.text) for c in retrieved_context]
    # Also include the retrieved citation labels themselves as exact anchors.
    anchors = [_normalize(c.statute_id) for c in retrieved_context]

    checks: list[CitationCheck] = []
    for citation in judgment.citations:
        key = _normalize(citation)
        matched_source = ""
        supported = False

        # Candidate substrings, from most to least specific.
        candidates = _candidates(key)
        if candidates:
            for candidate in candidates:
                for ctx, hay in zip(retrieved_context, haystacks):
                    if candidate and candidate in hay:
                        supported = True
                        matched_source = ctx.source
                        break
                if supported:
                    break

        note = (
            "Verified against retrieved law."
            if supported
            else "NOT found in retrieved law — possible hallucination."
        )
        checks.append(
            CitationCheck(
                citation=citation,
                supported=supported,
                matched_source=matched_source,
                note=note,
            )
        )
    return checks


def _candidates(key: str) -> list[str]:
    """Build progressive matching candidates from a normalized citation.

    e.g. 'king v perera 2024 slhc 0123' ->
      ['king v perera 2024 slhc 0123', 'king v perera 2024', 'king v perera',
       'king v perera', 'king v perera', 'king v']
    """
    if not key or len(key) < 4:
        return []
    out = [key]
    # Strip a trailing bracketed/year citation cluster.
    words = key.split()
    # Find where a year appears; treat everything from the year onward as
    # citation metadata.
    year_idx = next((i for i, w in enumerate(words) if w.isdigit() and len(w) == 4), None)
    if year_idx is not None:
        out.append(" ".join(words[:year_idx]))
        # Also try without the year-number but with prior words intact.
        if year_idx >= 2:
            out.append(" ".join(words[: year_idx - 1]))
    # Progressive word prefixes (case names / statute titles).
    n = len(words)
    for k in (3, 2):
        if n >= k:
            prefix = " ".join(words[:k])
            if prefix and len(prefix) >= 4 and prefix not in out:
                out.append(prefix)
    return out


def summarize(checks: list[CitationCheck]) -> dict:
    total = len(checks)
    supported = sum(1 for c in checks if c.supported)
    return {
        "total_citations": total,
        "supported": supported,
        "unsupported": total - supported,
        "citation_accuracy": round(supported / total, 4) if total else 1.0,
        "hallucinated": [c.citation for c in checks if not c.supported],
    }