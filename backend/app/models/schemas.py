from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CourtTier(str, Enum):
    SUPREME = "Supreme Court"
    APPEAL = "Court of Appeal"
    HIGH = "High Court"
    DISTRICT = "District Court"
    MAGISTRATE = "Magistrate Court"


class Proceeding(str, Enum):
    CRIMINAL = "criminal"
    CIVIL = "civil"


class CaseType(str, Enum):
    """Structural model of the case per the Sri Lankan legal corrections.

    - criminal: State/AG (prosecutor) vs Accused; victim is a witness.
    - civil: Plaintiff + counsel vs Defendant + counsel; no state, no police.
    - appeal: Appellant vs Respondent; briefs, not opening/evidence.
    """

    CRIMINAL = "criminal"
    CIVIL = "civil"
    APPEAL = "appeal"


class JudgeProfile(BaseModel):
    """One judge on the bench. A bench of N JudgeProfiles runs N judge calls."""

    id: str = "J1"
    name: str = "Judge 1 (pseudonym)"
    bench_index: int = 0
    is_presiding: bool = False
    role_note: str = ""


class BenchVerdict(BaseModel):
    """Aggregated result of a multi-judge bench."""

    majority_verdict: str = ""  # guilty | not_guilty | liable | not_liable
    per_judge: dict[str, str] = Field(default_factory=dict)  # judge_id -> verdict
    dissents: list[str] = Field(default_factory=list)  # judge_ids who dissented
    dissent_summary: str = ""


class Charge(BaseModel):
    """A single charge, mapped to a Penal Code / statute provision."""

    description: str
    statute: str = ""  # e.g. "Penal Code, s.324"
    section: str = ""
    max_penalty: str = ""


class EvidenceItem(BaseModel):
    type: str  # documentary | physical | witness | digital | hearsay...
    description: str
    relevance: str = ""
    admitted: bool | None = None


class Party(BaseModel):
    """A litigant — always hypothetical/anonymized. Never real identities."""

    name: str
    role: str = "accused"  # accused | plaintiff | defendant | victim | witness
    pseudonym: bool = True


class CaseInput(BaseModel):
    """Raw user / seeded input for a new case."""

    title: str
    court_tier: CourtTier = CourtTier.HIGH
    proceeding: Proceeding = Proceeding.CRIMINAL
    case_type: CaseType = CaseType.CRIMINAL
    jurisdiction: str = "Sri Lanka"
    parties: list[Party] = Field(default_factory=list)
    charges: list[Charge] = Field(default_factory=list)
    facts: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    burden_of_proof: str = Field(
        default="beyond reasonable doubt",
        description="civil: preponderance of the evidence",
    )
    bench: list[JudgeProfile] = Field(default_factory=list)


class StructuredCase(CaseInput):
    """The case file produced by the Intake agent (charges mapped to statutes)."""

    charges: list[Charge]
    mapped_offences: list[str] = Field(default_factory=list)
    intake_notes: str = ""


class TranscriptTurn(BaseModel):
    role: str  # intake | prosecution | defense | witness | judge | system
    speaker: str = ""
    label: str = ""
    content: str


class RetrievedContext(BaseModel):
    """Inline citation context retrieved for the Judge agent."""

    statute_id: str
    text: str
    relevance: float = 0.0
    source: str = "statute"  # statute | precedent | constitution


class Sentence(BaseModel):
    custodial: bool = False
    term_years: float | None = None
    term_months: float | None = None
    fine_lkr: float | None = None
    conditions: list[str] = Field(default_factory=list)
    note: str = ""


class CitationCheck(BaseModel):
    """Result of verifying a single citation against the retrieved corpus."""

    citation: str
    supported: bool
    matched_source: str = ""
    note: str = ""


class Judgment(BaseModel):
    facts_found: str
    legal_reasoning: str
    citations: list[str] = Field(default_factory=list)
    verdict: str  # guilty | not_guilty | liable | not_liable  (binary, no 'insufficient_evidence')
    verdict_confidence: float = 0.0
    # When the record is insufficient to convict, the judge either directs
    # the parties to produce more evidence ('produce_more') or acquits
    # ('acquit' == not_guilty). Default empty = a normal determination.
    evidentiary_directive: str = ""
    sentence: Sentence | None = None
    release: bool = False
    dissent_notes: str = ""
    bench_verdict: BenchVerdict | None = None
    methodology_warning: str = Field(
        default="AI simulation for research/education only — not a legal opinion."
    )


class CaseResult(BaseModel):
    case_title: str
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    retrieved_context: list[RetrievedContext] = Field(default_factory=list)
    judgment: Judgment | None = None
    status: str = "complete"
    citation_checks: list[CitationCheck] = Field(default_factory=list)


class TrialSnapshot(BaseModel):
    """A point-in-time view of a running/stepped trial for the frontend."""

    trial_id: str
    status: str  # running | complete | idle
    current_node: str = ""
    stage_label: str = ""
    steps_done: list[str] = Field(default_factory=list)
    steps_remaining: list[str] = Field(default_factory=list)
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    case: CaseInput | None = None
    judgment: Judgment | None = None
    retrieved_context: list[RetrievedContext] = Field(default_factory=list)
    citation_checks: list[CitationCheck] = Field(default_factory=list)


class HistoricalCase(BaseModel):
    """An anonymized/hypothetical historical case with a known outcome."""

    case: CaseInput
    ground_truth_verdict: str  # guilty | not_guilty | liable | not_liable
    notes: str = ""


class EvaluationResult(BaseModel):
    """Comparison of an AI verdict against a ground-truth outcome."""

    case_title: str
    predicted_verdict: str
    ground_truth_verdict: str
    correct: bool
    verdict_confidence: float = 0.0
    citation_accuracy: float = 0.0
    hallucinated_citations: list[str] = Field(default_factory=list)
    total_citations: int = 0
    notes: str = ""
    judgment: Judgment | None = None


class EvaluationReport(BaseModel):
    dataset_name: str = ""
    n_cases: int = 0
    correct: int = 0
    accuracy: float = 0.0
    mean_confidence: float = 0.0
    mean_citation_accuracy: float = 0.0
    hallucination_rate: float = 0.0
    results: list[EvaluationResult] = Field(default_factory=list)
    confusion: dict = Field(default_factory=dict)


class PromptRequest(BaseModel):
    """A text prompt sent to a generation helper (image or UI copy)."""

    prompt: str