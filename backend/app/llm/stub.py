from __future__ import annotations

from typing import Any

from app.llm.base import LLMProvider, Message


class StubProvider(LLMProvider):
    """Deterministic, offline placeholder so the full pipeline runs without a key.

    Emits role-aware text so you can verify the state machine, RAG retrieval,
    and API responses end-to-end before wiring a live model.
    """

    name = "stub"

    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, messages: list[Message], **kwargs: Any) -> str:
        self.call_count += 1
        system = next(
            (m.content for m in messages if m.role == "system"), ""
        )
        user = next((m.content for m in messages if m.role == "user"), "")

        if "You are a Judge" in system or "structured written judgment" in system:
            return _judge_json(user)

        if "Convert the raw case input into a structured case file" in system:
            return '{"mapped_offences": ["Penal Code, s.324 - voluntarily causing grievous hurt"], "intake_notes": "STUB: structured intake output."}'

        tag = self._detect_role(system)
        body = (
            f"[STUB {self.name}] {tag}: "
            f"Simulated {tag} submission for the hypothetical case. "
            f"Relies on the Sri Lankan Penal Code, Code of Criminal Procedure "
            f"Act, Evidence Ordinance, and cited precedents per the brief."
        )
        return body

    @staticmethod
    def _detect_role(system: str) -> str:
        low = system.lower()
        for name in ("intake", "prosecution", "defense", "witness", "closing", "judge"):
            if name in low:
                return name
        return "assistant"


_JUDGE_JSON = (
    '{"facts_found": "The accused struck the victim with a wooden crate in '
    'the course of a sudden market quarrel, fracturing the victim\'s arm.", '
    '"legal_reasoning": "STUB: The injury constitutes grievous hurt under '
    'Penal Code s.322. Applying s.324 and King v Perera, the absence of '
    'premeditation in a sudden quarrel weighs in mitigation.", '
    '"citations": ["Penal Code, s.324", "Penal Code, s.322", '
    '"King v Perera [2024] SLHC 0123"], "verdict": "guilty", '
    '"verdict_confidence": 0.85, "insufficient_evidence": false, '
    '"sentence": {"custodial": true, "term_years": 2, "term_months": 0, '
    '"fine_lkr": 50000, "conditions": ["good behaviour"], '
    '"note": "STUB sentence for offline demo"}, "release": false, '
    '"dissent_notes": ""}'
)


def _judge_json(user: str) -> str:
    """Heuristic stub judge: returns insufficient_evidence for weak records.

    This lets the offline evaluation demo demonstrate the no-verdict
    behaviour without a live model. A real model makes this determination
    from the record.
    """
    low = user.lower()
    weak_markers = [
        "no eyewitness",
        "no witness",
        "uncorroborated",
        "no admissible",
        "no independent",
        "no written contract",
        "no eyewitness to the entry",
        "bare receipt",
    ]
    if any(m in low for m in weak_markers):
        return (
            '{"facts_found": "The record does not establish the elements of '
            'the charge to the applicable burden of proof.", '
            '"legal_reasoning": "STUB: Essential elements are unproven - the '
            'admitted evidence does not cover the act or the required intent. '
            'The court therefore declines to convict and returns a verdict of '
            'insufficient evidence.", "citations": ["Penal Code, s.367"], '
            '"verdict": "insufficient_evidence", "verdict_confidence": 0.3, '
            '"insufficient_evidence": true, "sentence": null, "release": true, '
            '"dissent_notes": "STUB offline demo - insufficient evidence"}'
        )
    return _JUDGE_JSON