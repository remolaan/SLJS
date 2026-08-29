from __future__ import annotations

from app.agents.base import Agent
from app.models.schemas import StructuredCase


class ProsecutionAgent(Agent):
    """Opens the case, presents evidence, cites aggravating precedent."""

    role = "prosecution"
    system_prompt = (
        "You are the Prosecution (State Counsel) in an AI courtroom "
        "simulation for Sri Lanka. You present the case for the state "
        "against the accused. Duties: (1) deliver a clear opening statement "
        "setting out the charges and the facts you will prove; (2) present "
        "the evidence in order; (3) argue the legal elements and cite "
        "Sri Lankan law and aggravating precedent. Persuade but never invent "
        "facts beyond the case file. All parties are hypothetical."
    )

    def opening(self, case: StructuredCase) -> str:
        return self.run(self._context(case, stage="opening statement"))

    def evidence(self, case: StructuredCase) -> str:
        return self.run(self._context(case, stage="presentation of evidence"))

    def closing(self, case: StructuredCase) -> str:
        return self.run(self._context(case, stage="closing argument"))

    @staticmethod
    def _context(case: StructuredCase, stage: str) -> str:
        return (
            f"CASE: {case.title}\nCourt: {case.court_tier.value}\n"
            f"Accused: {', '.join(p.name for p in case.parties if p.role=='accused')}\n"
            f"Charges: {case.charges}\nMapped offences: {case.mapped_offences}\n"
            f"Facts: {case.facts}\nEvidence: {[e.description for e in case.evidence]}\n"
            f"\nSTAGE: {stage}. Provide your submission for this stage."
        )


class DefenseAgent(Agent):
    """Responds, raises mitigating factors and procedural challenges."""

    role = "defense"
    system_prompt = (
        "You are the Defense Counsel in an AI courtroom simulation for Sri "
        "Lanka. You represent the accused. Duties: (1) respond to the "
        "prosecution's case; (2) present mitigating factors; (3) raise "
        "procedural or evidentiary challenges where warranted; (4) cite "
        "Sri Lankan law and favorable precedent. Challenge only on legitimate "
        "legal grounds, never by inventing facts. All parties are hypothetical."
    )

    def opening(self, case: StructuredCase, prosecution_statement: str) -> str:
        return self.run(
            self._context(case, stage="response / defense opening", opponent=prosecution_statement)
        )

    def evidence(self, case: StructuredCase) -> str:
        return self.run(self._context(case, stage="defense evidence"))

    def closing(self, case: StructuredCase, prosecution_closing: str) -> str:
        return self.run(
            self._context(case, stage="closing argument", opponent=prosecution_closing)
        )

    @staticmethod
    def _context(case: StructuredCase, stage: str, opponent: str = "") -> str:
        return (
            f"CASE: {case.title}\nCourt: {case.court_tier.value}\n"
            f"Accused: {', '.join(p.name for p in case.parties if p.role=='accused')}\n"
            f"Charges: {case.charges}\nFacts: {case.facts}\n"
            f"Defense evidence: {[e.description for e in case.evidence if 'defense' in e.type.lower()]}\n"
            + (f"\nOpposing submission:\n{opponent}\n" if opponent else "")
            + f"\nSTAGE: {stage}. Provide your submission."
        )


class WitnessAgent(Agent):
    """Generates testimony consistent with the case facts; supports cross-exam."""

    role = "witness"
    system_prompt = (
        "You are a Witness/Victim in an AI courtroom simulation for Sri "
        "Lanka. Generate testimony that is CONSISTENT with the case facts "
        "provided — do not add new facts or contradict the record. In "
        "cross-examination, answer questions directly and honestly, and "
        "admit uncertainty where the record is unclear. You are a "
        "hypothetical character; do not resemble any real person."
    )

    def testify(self, case: StructuredCase, witness_name: str) -> str:
        return self.run(
            f"CASE: {case.title}\nFacts: {case.facts}\n"
            f"Evidence: {[e.description for e in case.evidence]}\n"
            f"\nYou are {witness_name}. Give your examination-in-chief "
            f"testimony consistent with these facts."
        )

    def cross_examine(self, case: StructuredCase, witness_name: str, question: str) -> str:
        return self.run(
            f"CASE: {case.title}\nFacts: {case.facts}\n\n"
            f"You are {witness_name}. Cross-examination question: {question}"
        )


class ClosingAgent(Agent):
    """Runs closing arguments for both sides from one role object."""

    role = "closing"
    system_prompt = (
        "You deliver closing arguments in an AI courtroom simulation for "
        "Sri Lanka. Summarize the evidence, apply the law to the facts, and "
        "urge the court toward the appropriate outcome. You may speak for "
        "either the prosecution or the defense; follow the side you are asked "
        "to represent. All parties are hypothetical."
    )

    def for_side(self, side: str, case: StructuredCase, transcript_so_far: str) -> str:
        return self.run(
            f"Represent the {side}. CASE: {case.title}\nCharges: {case.charges}\n"
            f"Facts: {case.facts}\n\nTranscript so far:\n{transcript_so_far}\n\n"
            f"Deliver your closing argument for the {side}."
        )


class JudgeAgent(Agent):
    """Weighs both sides, applies burden of proof, issues structured judgment."""

    role = "judge"
    system_prompt = (
        "You are a Judge in an AI courtroom simulation for Sri Lanka. Your "
        "duty is to weigh the prosecution and defense submissions, apply the "
        "correct burden of proof, and deliver a structured written judgment "
        "in the style of a Sri Lankan court. Ground your reasoning in the "
        "RETRIEVED LAW provided (statute sections and precedent) and cite "
        "them inline. Never cite law that is not in the retrieved context. "
        "This is a research/education simulation, not a real legal opinion.\n"
        "\nCRITICAL — do not force a verdict: If the record (facts, evidence, "
        "and testimony) is insufficient to establish the elements of the "
        "charge to the applicable burden of proof — for example because "
        "essential evidence is missing, eyewitness evidence is absent, or "
        "admitted evidence does not cover a required element — you MUST "
        "decline to convict. Set \"verdict\": \"insufficient_evidence\", "
        "\"insufficient_evidence\": true, and explain in legal_reasoning what "
        "element is unproven. Only return a guilty/not_guilty verdict when "
        "the record genuinely supports a determination.\n"
        "Return ONLY valid JSON with keys:\n"
        '{"facts_found": "...", "legal_reasoning": "...", '
        '"citations": ["..."], "verdict": "guilty|not_guilty|liable|'
        'not_liable|insufficient_evidence", "verdict_confidence": 0.0-1.0, '
        '"insufficient_evidence": bool, '
        '"sentence": {"custodial": bool, "term_years": num|null, '
        '"term_months": num|null, "fine_lkr": num|null, "conditions": [], '
        '"note": "..."}, "release": bool, "dissent_notes": "..."}'
    )

    def judge(
        self,
        case: StructuredCase,
        transcript: list,
        retrieved_context: list,
    ) -> str:
        context_txt = (
            "\n".join(f"[{c.source}][rel {c.relevance}] {c.text}" for c in retrieved_context)
            or "(No law retrieved — reason on general principles only.)"
        )
        transcript_txt = "\n".join(f"[{t.role}] {t.content}" for t in transcript)
        prompt = (
            f"CASE: {case.title}\nCourt: {case.court_tier.value}\n"
            f"Proceeding: {case.proceeding.value}\n"
            f"Burden of proof: {case.burden_of_proof}\n"
            f"Charges: {case.charges}\nMapped offences: {case.mapped_offences}\n"
            f"Facts: {case.facts}\n"
            f"\nRETRIEVED LAW (cite only from here):\n{context_txt}\n"
            f"\nFULL TRIAL TRANSCRIPT:\n{transcript_txt}\n"
            f"\nDeliver your structured judgment as JSON."
        )
        return self.run(prompt)


class ExaminerAgent(Agent):
    """Answers interactive questions (judge questions counsel/witness)."""

    role = "examiner"

    @classmethod
    def for_role(cls, role: str, llm=None) -> "ExaminerAgent":
        self = cls.__new__(cls)
        self.role = role
        self.llm = llm
        if role == "witness":
            self.system_prompt = (
                "You are a witness in an AI courtroom simulation for Sri "
                "Lanka. Answer the question truthfully and consistently with "
                "the case facts; admit uncertainty where the record is "
                "unclear. You are a hypothetical character."
            )
        elif role == "judge":
            self.system_prompt = (
                "You are the Judge in an AI courtroom simulation for Sri "
                "Lanka. Ask a focused, fair clarifying question to the "
                "addressee (counsel or witness) based only on the case file "
                "and the record so far. One concise question."
            )
        else:
            self.system_prompt = (
                f"You are the {role} counsel in an AI courtroom simulation "
                "for Sri Lanka. Respond directly to the question asked by "
                "the court, on the record, citing law where relevant. All "
                "parties are hypothetical."
            )
        return self

    def answer(self, case: StructuredCase, question: str, speaker: str) -> str:
        return self.run(
            f"CASE: {case.title}\nFacts: {case.facts}\n"
            f"Evidence: {[e.description for e in case.evidence]}\n\n"
            f"You are {speaker}. Question asked:\n{question}\n\n"
            f"Give your response."
        )

    def ask(self, case: StructuredCase, transcript_so_far: str, addressee: str) -> str:
        return self.run(
            f"CASE: {case.title}\nFacts: {case.facts}\n"
            f"Addressee: {addressee}\nRecord so far:\n{transcript_so_far}\n\n"
            f"Pose your question."
        )