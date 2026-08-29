from __future__ import annotations

from app.models.schemas import (
    CaseInput,
    Charge,
    CourtTier,
    EvidenceItem,
    HistoricalCase,
    Party,
    Proceeding,
)


def _grievous_hurt(include_witness_evidence: bool, verdict: str, note: str) -> HistoricalCase:
    evidence = [
        EvidenceItem(type="documentary", description="Hospital record documenting an arm fracture.", relevance="establishes grievous hurt under s.322"),
    ]
    if include_witness_evidence:
        evidence.append(
            EvidenceItem(type="witness", description="Two bystanders who saw the accused strike the victim during a quarrel.", relevance="corroborates the act and the sudden quarrel")
        )
    return HistoricalCase(
        case=CaseInput(
            title="Anonymized Case A — Market Assault",
            court_tier=CourtTier.HIGH,
            proceeding=Proceeding.CRIMINAL,
            parties=[Party(name="Accused A (pseudonym)", role="accused"), Party(name="Victim (pseudonym)", role="victim")],
            charges=[Charge(description="voluntarily causing grievous hurt", statute="Penal Code", section="324", max_penalty="up to 7 years")],
            facts=(
                "The accused and the victim argued over a market stall. In the "
                "course of a sudden quarrel the accused struck the victim, "
                "fracturing the victim's arm. The accused claims no prior "
                "planning and that the blow occurred in the heat of the moment."
            ),
            evidence=evidence,
            burden_of_proof="beyond reasonable doubt",
        ),
        ground_truth_verdict=verdict,
        notes=note,
    )


def _theft_no_eyewitness(verdict: str, note: str) -> HistoricalCase:
    return HistoricalCase(
        case=CaseInput(
            title="Anonymized Case B — Shophouse Theft",
            court_tier=CourtTier.HIGH,
            proceeding=Proceeding.CRIMINAL,
            parties=[Party(name="Accused B (pseudonym)", role="accused"), Party(name="Shopkeeper (pseudonym)", role="victim")],
            charges=[Charge(description="theft of movable property", statute="Penal Code", section="367")],
            facts=(
                "A shophouse was entered after sunset by forcing the rear lock "
                "and goods were removed. The accused was found nearby in "
                "possession of some goods but there was no eyewitness to the "
                "entry and no admissible admission. The accused states he found "
                "the goods abandoned."
            ),
            evidence=[
                EvidenceItem(type="circumstantial", description="Accused found in possession of goods shortly after.", relevance="recent possession"),
                EvidenceItem(type="physical", description="Forced rear lock.", relevance="house entry"),
            ],
            burden_of_proof="beyond reasonable doubt",
        ),
        ground_truth_verdict=verdict,
        notes=note,
    )


def _fraud_no_documentation(verdict: str, note: str) -> HistoricalCase:
    return HistoricalCase(
        case=CaseInput(
            title="Anonymized Case C — Alleged Cheating",
            court_tier=CourtTier.DISTRICT,
            proceeding=Proceeding.CIVIL,
            parties=[Party(name="Claimant (pseudonym)", role="plaintiff"), Party(name="Respondent (pseudonym)", role="defendant")],
            charges=[Charge(description="cheating / fraudulent inducement", statute="Penal Code", section="400")],
            facts=(
                "The claimant alleges the respondent induced payment of a "
                "deposit by false promises and then failed to perform. The "
                "respondent denies any misrepresentation. There is no written "
                "contract, no contemporaneous record of the alleged promises, "
                "and no documentary evidence beyond a bare receipt for the "
                "deposit."
            ),
            evidence=[
                EvidenceItem(type="documentary", description="A bare receipt for the deposit, without terms.", relevance="shows payment only"),
                EvidenceItem(type="witness", description="The claimant's own account; no independent witness.", relevance="uncorroborated"),
            ],
            burden_of_proof="preponderance of the evidence",
        ),
        ground_truth_verdict=verdict,
        notes=note,
    )


def _grievous_hurt_strong_case(verdict: str, note: str) -> HistoricalCase:
    return HistoricalCase(
        case=CaseInput(
            title="Anonymized Case D — Strong Assault Case",
            court_tier=CourtTier.HIGH,
            proceeding=Proceeding.CRIMINAL,
            parties=[Party(name="Accused D (pseudonym)", role="accused"), Party(name="Victim (pseudonym)", role="victim")],
            charges=[Charge(description="voluntarily causing grievous hurt", statute="Penal Code", section="324")],
            facts=(
                "The accused, in a premeditated confrontation, struck the "
                "victim with an iron bar, causing a compound fracture of the "
                "leg. Multiple independent witnesses gave consistent accounts, "
                "and the weapon was recovered. There was no provocation and no "
                "sudden quarrel."
            ),
            evidence=[
                EvidenceItem(type="witness", description="Three independent witnesses with consistent accounts.", relevance="strong corroboration"),
                EvidenceItem(type="physical", description="Iron bar recovered and matched to the injury.", relevance="weapon"),
                EvidenceItem(type="documentary", description="Hospital record of a compound leg fracture.", relevance="grievous hurt"),
            ],
            burden_of_proof="beyond reasonable doubt",
        ),
        ground_truth_verdict=verdict,
        notes=note,
    )


HISTORICAL_DATASET = [
    _grievous_hurt(
        include_witness_evidence=True,
        verdict="guilty",
        note="Eye-witnesses corroborate the act; fracture is grievous hurt.",
    ),
    _grievous_hurt(
        include_witness_evidence=False,
        verdict="insufficient_evidence",
        note="No witness to the act and the accused disputes it; elements unproven.",
    ),
    _theft_no_eyewitness(
        verdict="insufficient_evidence",
        note="Only recent possession; no proof of dishonest taking/entry beyond reasonable doubt.",
    ),
    _fraud_no_documentation(
        verdict="insufficient_evidence",
        note="Bare receipt and uncorroborated account do not prove misrepresentation.",
    ),
    _grievous_hurt_strong_case(
        verdict="guilty",
        note="Multiple consistent witnesses and weapon; strong case.",
    ),
]

DATASET_NAME = "anonymized_demo_dataset"
