from __future__ import annotations

import json
import re

from app.agents.base import Agent
from app.models.schemas import Charge, StructuredCase


class IntakeAgent(Agent):
    """Structures raw input into a formal case file with mapped charges.

    Runs early in the pipeline to give downstream agents a normalized case
    object. With the stub provider it returns deterministic JSON.
    """

    role = "intake"
    system_prompt = (
        "You are the Case Intake Officer in an AI courtroom simulation for "
        "Sri Lanka. Convert the raw case input into a structured case file. "
        "Map each charge to the most relevant Penal Code (Ordinance No. 2 of "
        "1883) or other statute section. Return ONLY valid JSON with keys:\n"
        '{"mapped_offences": ["<statute> s.<n> - <short label>", ...], '
        '"intake_notes": "<one-paragraph summary>"}.\n'
        "All litigants are hypothetical; never invent or use real identities. "
        "If charge elements are missing, note that in intake_notes rather "
        "than guessing."
    )

    def process(self, case) -> StructuredCase:
        prompt = (
            f"Title: {case.title}\nCourt: {case.court_tier.value} "
            f"({case.proceeding.value})\nParties: "
            f"{', '.join(f'{p.name} ({p.role})' for p in case.parties)}\n"
            f"Charges: {case.charges}\nFacts: {case.facts}\n"
            f"Evidence: {[e.description for e in case.evidence]}"
        )
        raw = self.run(prompt)

        structured = StructuredCase(**case.model_dump())
        mapped, notes = self._parse(raw)
        structured.mapped_offences = mapped
        structured.intake_notes = notes
        return structured

    @staticmethod
    def _parse(raw: str) -> tuple[list[str], str]:
        try:
            m = re.search(r"\{.*\}", raw, re.S)
            data = json.loads(m.group(0)) if m else json.loads(raw)
            return data.get("mapped_offences", []), data.get("intake_notes", "")
        except (json.JSONDecodeError, AttributeError):
            return [], raw.strip()[:500]