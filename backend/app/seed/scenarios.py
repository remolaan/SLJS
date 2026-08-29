from __future__ import annotations

from app.models.schemas import (
    CaseInput,
    CaseType,
    Charge,
    CourtTier,
    EvidenceItem,
    JudgeProfile,
    Party,
    Proceeding,
)


def _bench(n, prefix="J"):
    judges = []
    for i in range(n):
        judges.append(
            JudgeProfile(
                id=f"{prefix}{i+1}",
                name=f"Judge {i+1} (pseudonym)",
                bench_index=i,
                is_presiding=(i == 0),
            )
        )
    return judges


def minor_criminal() -> CaseInput:
    """Magistrate's Court: Police vs Accused, minor offence, 1 judge."""
    return CaseInput(
        title="Minor Theft Before the Magistrate (Hypothetical)",
        court_tier=CourtTier.MAGISTRATE,
        proceeding=Proceeding.CRIMINAL,
        case_type=CaseType.CRIMINAL,
        parties=[Party(name="Police (prosecutor)", role="accused"), Party(name="K. Perera (pseudonym)", role="witness")],
        charges=[Charge(description="theft of movable property", statute="Penal Code", section="367")],
        facts=(
            "A small amount of cash was taken from a market stall. The accused "
            "was found shortly after in possession of the cash. Two witnesses "
            "saw the accused near the stall."
        ),
        evidence=[
            EvidenceItem(type="witness", description="Two bystanders saw the accused near the stall."),
            EvidenceItem(type="circumstantial", description="Accused found in possession of the cash."),
        ],
        burden_of_proof="beyond reasonable doubt",
        bench=_bench(1),
    )


def serious_criminal() -> CaseInput:
    """High Court (ordinary): AG vs Accused, victim as witness, 1 judge."""
    return CaseInput(
        title="Grievous Hurt in the High Court (Hypothetical)",
        court_tier=CourtTier.HIGH,
        proceeding=Proceeding.CRIMINAL,
        case_type=CaseType.CRIMINAL,
        parties=[Party(name="A. Bandara (pseudonym)", role="accused"), Party(name="K. Nadeesha (pseudonym)", role="witness")],
        charges=[Charge(description="voluntarily causing grievous hurt", statute="Penal Code", section="324")],
        facts=(
            "A market-day dispute escalated; the accused struck the victim "
            "with a wooden crate, fracturing the victim's arm."
        ),
        evidence=[
            EvidenceItem(type="witness", description="Two bystanders saw the strike."),
            EvidenceItem(type="documentary", description="Hospital record of an arm fracture."),
            EvidenceItem(type="physical", description="The wooden crate."),
        ],
        burden_of_proof="beyond reasonable doubt",
        bench=_bench(1),
    )


def trial_at_bar() -> CaseInput:
    """Trial-at-Bar: AG vs Accused, high-profile/financial, 3-judge bench."""
    return CaseInput(
        title="Financial Fraud Trial-at-Bar (Hypothetical)",
        court_tier=CourtTier.HIGH,
        proceeding=Proceeding.CRIMINAL,
        case_type=CaseType.CRIMINAL,
        parties=[Party(name="D. Wijesuriya (pseudonym)", role="accused"), Party(name="Bank Officer (pseudonym)", role="witness")],
        charges=[Charge(description="cheating / fraud", statute="Penal Code", section="400")],
        facts=(
            "A complex financial scheme allegedly defrauded investors. Many "
            "documents and several witnesses; high public interest; heard by a "
            "three-judge bench."
        ),
        evidence=[
            EvidenceItem(type="documentary", description="Bank statements and contracts."),
            EvidenceItem(type="witness", description="Investors and a forensic accountant."),
        ],
        burden_of_proof="beyond reasonable doubt",
        bench=_bench(3),
    )


def civil_dispute() -> CaseInput:
    """District Court: Plaintiff vs Defendant, private suit, 1 judge."""
    return CaseInput(
        title="Breach of Contract (Hypothetical)",
        court_tier=CourtTier.DISTRICT,
        proceeding=Proceeding.CIVIL,
        case_type=CaseType.CIVIL,
        parties=[Party(name="M. Weerasinghe (pseudonym)", role="plaintiff"), Party(name="S. Fernando (pseudonym)", role="defendant")],
        charges=[Charge(description="breach of contract / recovery of sum", statute="Civil Law")],
        facts=(
            "The plaintiff paid a deposit for goods that were never delivered "
            "and seeks recovery. The defendant disputes the terms."
        ),
        evidence=[
            EvidenceItem(type="documentary", description="A receipt for the deposit."),
            EvidenceItem(type="witness", description="The plaintiff's account; no independent witness."),
        ],
        burden_of_proof="preponderance of the evidence",
        bench=_bench(1),
    )


def criminal_appeal() -> CaseInput:
    """Court of Appeal: Appellant vs Respondent (AG), 3-judge bench."""
    return CaseInput(
        title="Appeal Against Conviction (Hypothetical)",
        court_tier=CourtTier.APPEAL,
        proceeding=Proceeding.CRIMINAL,
        case_type=CaseType.APPEAL,
        parties=[Party(name="Appellant (pseudonym)", role="accused"), Party(name="Attorney-General", role="respondent")],
        charges=[Charge(description="appeal on grounds of misdirection", statute="Court of Appeal Rules")],
        facts=(
            "The appellant was convicted in the High Court and appeals, arguing "
            "the trial judge misdirected the jury on the burden of proof."
        ),
        evidence=[EvidenceItem(type="documentary", description="The trial record and judgment.")],
        burden_of_proof="on appeal, per the grounds",
        bench=_bench(3),
    )


def constitutional_appeal() -> CaseInput:
    """Supreme Court: Petitioner vs Respondent, 3/5/7-judge bench."""
    return CaseInput(
        title="Fundamental Rights Application (Hypothetical)",
        court_tier=CourtTier.SUPREME,
        proceeding=Proceeding.CIVIL,
        case_type=CaseType.APPEAL,
        parties=[Party(name="Petitioner (pseudonym)", role="plaintiff"), Party(name="Respondent (pseudonym)", role="defendant")],
        charges=[Charge(description="fundamental rights / constitutional", statute="Constitution of Sri Lanka, Art. 12-13")],
        facts=(
            "A constitutional question about equal protection and the right to "
            "liberty is raised. Heard by a multi-judge bench of the Supreme "
            "Court."
        ),
        evidence=[EvidenceItem(type="documentary", description="The petition and record.")],
        burden_of_proof="per the constitutional standard",
        bench=_bench(5),
    )


SCENARIOS = {
    "minor_criminal": minor_criminal,
    "serious_criminal": serious_criminal,
    "trial_at_bar": trial_at_bar,
    "civil_dispute": civil_dispute,
    "criminal_appeal": criminal_appeal,
    "constitutional_appeal": constitutional_appeal,
}
