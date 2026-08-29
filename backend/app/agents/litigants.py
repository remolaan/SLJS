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


# --- scenario-aware civil / appeal counsel ------------------------------------

class PlaintiffCounselAgent(Agent):
    """Civil: represents the plaintiff (private party) against the defendant."""

    role = "plaintiff"
    system_prompt = (
        "You are the Plaintiff's Counsel in a Sri Lankan civil action. You act "
        "for a private party (the plaintiff), not the state. There is no "
        "police or prosecutor. Duties: (1) open the claim and state the "
        "relief sought; (2) present the plaintiff's evidence; (3) argue the "
        "civil burden of proof (preponderance of the evidence). Never invent "
        "facts beyond the case file. All parties are hypothetical."
    )

    def opening(self, case: StructuredCase) -> str:
        return self.run(self._ctx(case, "opening statement"))
    def evidence(self, case: StructuredCase) -> str:
        return self.run(self._ctx(case, "presentation of plaintiff's evidence"))
    def closing(self, case: StructuredCase) -> str:
        return self.run(self._ctx(case, "closing argument"))

    @staticmethod
    def _ctx(case: StructuredCase, stage: str) -> str:
        return (
            f"CASE: {case.title}\nCourt: {case.court_tier.value}\n"
            f"Proceeding: civil\nBurden: {case.burden_of_proof}\n"
            f"Plaintiff: {', '.join(p.name for p in case.parties if p.role=='plaintiff')}\n"
            f"Facts: {case.facts}\nEvidence: {[e.description for e in case.evidence]}\n"
            f"\nSTAGE: {stage}."
        )


class DefendantCounselAgent(Agent):
    """Civil: represents the defendant (private party)."""

    role = "defendant"
    system_prompt = (
        "You are the Defendant's Counsel in a Sri Lankan civil action. You act "
        "for a private party (the defendant) against the plaintiff. There is "
        "no state involvement. Duties: (1) respond to the plaintiff's claim; "
        "(2) raise defences and mitigating or exculpatory matters; (3) cite "
        "civil law. Never invent facts. All parties are hypothetical."
    )

    def opening(self, case: StructuredCase, plaintiff_statement: str) -> str:
        return self.run(self._ctx(case, "response", plaintiff_statement))
    def evidence(self, case: StructuredCase) -> str:
        return self.run(self._ctx(case, "defendant's evidence"))
    def closing(self, case: StructuredCase, plaintiff_closing: str) -> str:
        return self.run(self._ctx(case, "closing argument", plaintiff_closing))

    @staticmethod
    def _ctx(case: StructuredCase, stage: str, opponent: str = "") -> str:
        return (
            f"CASE: {case.title}\nCourt: {case.court_tier.value}\n"
            f"Proceeding: civil\nBurden: {case.burden_of_proof}\n"
            f"Defendant: {', '.join(p.name for p in case.parties if p.role=='defendant')}\n"
            f"Facts: {case.facts}\n"
            + (f"\nOpposing submission:\n{opponent}\n" if opponent else "")
            + f"\nSTAGE: {stage}."
        )


class AppellantCounselAgent(Agent):
    """Appeal: represents the appellant on appeal (criminal or civil)."""

    role = "appellant"
    system_prompt = (
        "You are counsel for the Appellant in a Sri Lankan appeal. You "
        "challenge the decision below on the grounds of appeal (error of law, "
        "misdirection, procedural error, or error on the evidence). You "
        "present written/argument-based briefs, not a fresh opening or "
        "evidence. Never invent facts. All parties are hypothetical."
    )

    def brief(self, case: StructuredCase) -> str:
        return self.run(self._ctx(case, "appellant's submissions"))

    def opening(self, case: StructuredCase) -> str:
        return self.brief(case)
    def evidence(self, case: StructuredCase) -> str:
        return self.brief(case)
    def closing(self, case: StructuredCase, opponent: str = "") -> str:
        return self.brief(case)

    @staticmethod
    def _ctx(case: StructuredCase, stage: str) -> str:
        return (
            f"CASE: {case.title}\nCourt: {case.court_tier.value}\n"
            f"Proceeding: {case.case_type.value}\nFacts: {case.facts}\n"
            f"\nSTAGE: {stage}."
        )


class RespondentCounselAgent(Agent):
    """Appeal: represents the respondent (AG or other side) in defence of the decision."""

    role = "respondent"
    system_prompt = (
        "You are counsel for the Respondent in a Sri Lankan appeal. You "
        "defend the decision below against the appellant's grounds of appeal, "
        "on the record and on the law. Never invent facts. All parties are "
        "hypothetical."
    )

    def brief(self, case: StructuredCase, appellant_brief: str = "") -> str:
        return self.run(
            f"CASE: {case.title}\nCourt: {case.court_tier.value}\n"
            f"Facts: {case.facts}\n\nAppellant's submissions:\n{appellant_brief}\n\n"
            f"Deliver the respondent's submissions."
        )

    def opening(self, case: StructuredCase, opponent: str = "") -> str:
        return self.brief(case, opponent)
    def evidence(self, case: StructuredCase) -> str:
        return self.brief(case)
    def closing(self, case: StructuredCase, opponent: str = "") -> str:
        return self.brief(case, opponent)

    @staticmethod
    def _ctx(case: StructuredCase, stage: str) -> str:
        return (
            f"CASE: {case.title}\nCourt: {case.court_tier.value}\n"
            f"Proceeding: {case.case_type.value}\nFacts: {case.facts}\n"
            f"\nSTAGE: {stage}."
        )


def counsel_for(case_type, side):
    """Return the appropriate counsel agent class for a scenario + side."""
    from app.models.schemas import CaseType

    if case_type == CaseType.CIVIL:
        return PlaintiffCounselAgent if side in ("plaintiff", "prosecution", "appellant") else DefendantCounselAgent
    if case_type == CaseType.APPEAL:
        return AppellantCounselAgent if side in ("appellant", "plaintiff", "prosecution") else RespondentCounselAgent
    # criminal: state prosecutor vs defense
    return ProsecutionAgent if side in ("prosecution", "plaintiff", "appellant") else DefenseAgent


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
        "\nCRITICAL — verdicts are BINARY (guilty/not_guilty, or liable/"
        "not_liable in civil). You must NEVER return 'insufficient_evidence' "
        "as a verdict. If the record (facts, evidence, testimony) is "
        "insufficient to establish the elements to the applicable burden of "
        "proof:\n"
        "  - If the prosecution/plaintiff could still remedy the gap, set "
        "\"verdict\": \"not_guilty\", \"release\": false, and "
        "\"evidentiary_directive\": \"produce_more\", then state in "
        "legal_reasoning what element is unproven and what further evidence "
        "should be produced.\n"
        "  - If the case should simply end, set \"verdict\": \"not_guilty\", "
        "\"release\": true, and \"evidentiary_directive\": \"acquit\".\n"
        "Otherwise return a clear guilty/not_guilty (or liable/not_liable) "
        "verdict with no directive.\n"
        "Return ONLY valid JSON with keys:\n"
        '{"facts_found": "...", "legal_reasoning": "...", '
        '"citations": ["..."], "verdict": "guilty|not_guilty|liable|'
        'not_liable", "verdict_confidence": 0.0-1.0, '
        '"evidentiary_directive": ""|"produce_more"|"acquit", '
        '"sentence": {"custodial": bool, "term_years": num|null, '
        '"term_months": num|null, "fine_lkr": num|null, "conditions": [], '
        '"note": "..."}, "release": bool, "dissent_notes": "..."}'
    )

    def judge(
        self,
        case: StructuredCase,
        transcript: list,
        retrieved_context: list,
        judge_profile=None,
    ) -> str:
        context_txt = (
            "\n".join(f"[{c.source}][rel {c.relevance}] {c.text}" for c in retrieved_context)
            or "(No law retrieved — reason on general principles only.)"
        )
        transcript_txt = "\n".join(f"[{t.role}] {t.content}" for t in transcript)
        bench_txt = ""
        if judge_profile is not None:
            bench_txt = (
                f"\nYou are {judge_profile.name} (judge {judge_profile.bench_index + 1} "
                f"of a {case.bench.__len__() if case.bench else 1}-judge bench)."
                + (" You are the presiding judge." if judge_profile.is_presiding else "")
                + " Deliver your own independent judgment; do not assume what the other judges decide.\n"
            )
        prompt = (
            f"CASE: {case.title}\nCourt: {case.court_tier.value}\n"
            f"Proceeding: {case.case_type.value}\n"
            f"Burden of proof: {case.burden_of_proof}\n"
            f"Charges: {case.charges}\nMapped offences: {case.mapped_offences}\n"
            f"Facts: {case.facts}\n"
            f"{bench_txt}"
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