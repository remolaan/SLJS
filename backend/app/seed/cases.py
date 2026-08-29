from __future__ import annotations

from app.models.schemas import (
    CaseInput,
    Charge,
    CourtTier,
    EvidenceItem,
    Party,
    Proceeding,
)


def the_market_altercation() -> CaseInput:
    """Hypothetical: sudden-quarrel grievous hurt. No real persons."""
    return CaseInput(
        title="The Market Altercation (Hypothetical)",
        court_tier=CourtTier.HIGH,
        proceeding=Proceeding.CRIMINAL,
        parties=[
            Party(name="A. Bandara (pseudonym)", role="accused"),
            Party(name="K. Nadeesha (pseudonym)", role="victim"),
        ],
        charges=[
            Charge(
                description="voluntarily causing grievous hurt",
                statute="Penal Code",
                section="324",
                max_penalty="imprisonment up to 7 years and fine",
            )
        ],
        facts=(
            "On a market day, a dispute arose between two vendors over a "
            "stall boundary. The argument escalated and the accused struck "
            "the victim with a wooden crate, fracturing the victim's arm. "
            "The accused claims the blow was struck in the heat of a sudden "
            "quarrel and without prior planning. The victim was treated at "
            "a hospital and discharged after ten days."
        ),
        evidence=[
            EvidenceItem(
                type="witness",
                description="Two bystanders who saw the altercation begin and escalate.",
                relevance="corroborates sudden quarrel / provocation",
            ),
            EvidenceItem(
                type="documentary",
                description="Hospital admission record documenting the arm fracture.",
                relevance="establishes grievous hurt under s.322",
            ),
            EvidenceItem(
                type="physical",
                description="The wooden crate recovered at the scene.",
                relevance="corroborates the manner of injury",
            ),
        ],
        burden_of_proof="beyond reasonable doubt",
    )


def the_shophouse_theft() -> CaseInput:
    """Hypothetical: night house-breaking and theft. No real persons."""
    return CaseInput(
        title="The Shophouse Theft (Hypothetical)",
        court_tier=CourtTier.HIGH,
        proceeding=Proceeding.CRIMINAL,
        parties=[
            Party(name="S. Fernando (pseudonym)", role="accused"),
            Party(name="M. Weerasinghe (pseudonym)", role="victim"),
        ],
        charges=[
            Charge(
                description="theft of movable property",
                statute="Penal Code",
                section="367",
                max_penalty="imprisonment",
            ),
            Charge(
                description="house-trespass by night",
                statute="Penal Code",
                section="431",
                max_penalty="imprisonment",
            ),
        ],
        facts=(
            "A shophouse was entered after sunset by forcing the rear lock. "
            "Cash and goods were removed. The accused was found nearby with "
            "some of the goods. The accused denied the entry, stating he "
            "found the goods abandoned. There was no direct eyewitness to "
            "the entry."
        ),
        evidence=[
            EvidenceItem(
                type="physical",
                description="Forced lock and recovered goods matched to the shophouse.",
                relevance="connects accused to the property",
            ),
            EvidenceItem(
                type="circumstantial",
                description="Accused found in possession of the goods shortly after.",
                relevance="recent possession inference",
            ),
        ],
        burden_of_proof="beyond reasonable doubt",
    )


SEED_CASES = {
    "market_altercation": the_market_altercation,
    "shophouse_theft": the_shophouse_theft,
}