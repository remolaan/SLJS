from __future__ import annotations

from app.models.schemas import RetrievedContext, StructuredCase
from app.rag.store import get_vectorstore

# Legal elements / keywords mapped to charge descriptions. Used to build a
# richer retrieval query from the charges the Intake agent produced.
CHARGE_HINTS = {
    "grievous hurt": "grievous hurt Penal Code section 322 323 324",
    "hurt": "hurt Penal Code section 314 315 assault",
    "theft": "theft dishonestly taking movable property Penal Code 367 368 369",
    "robbery": "robbery theft violence Penal Code 380 381",
    "burglary": "house breaking by night burglary Penal Code 431",
    "murder": "murder culpable homicide Penal Code 294 296 297",
    "manslaughter": "culpable homicide not amounting to murder 296 297",
    "rape": "rape sexual assault Penal Code 363 364 365",
    "fraud": "cheating fraud Penal Code 400 403",
    "bribery": "bribery corruption Bribery Act",
    "criminal breach of trust": "criminal breach of trust Penal Code 392",
    "assault": "assault use of criminal force Penal Code 326 327 328",
}


def _statute_query(charges) -> str:
    terms = []
    for c in charges:
        key = c.description.lower()
        for hint_key, hint in CHARGE_HINTS.items():
            if hint_key in key:
                terms.append(hint)
                break
        if c.section:
            terms.append(f"Penal Code section {c.section}")
    if not terms:
        terms = [" ".join(c.description for c in charges)]
    return " ".join(terms)


def _precedent_query(case: StructuredCase) -> str:
    facts = case.facts[:1200]
    charges = " ".join(c.description for c in case.charges)
    return f"{charges}. {facts}"


def retrieve_for_judge(case: StructuredCase, settings) -> list[RetrievedContext]:
    """Retrieve statute sections (by charge) + precedent (by fact pattern)."""
    store = get_vectorstore(settings)
    context: list[RetrievedContext] = []

    if store.count() == 0:
        return context

    try:
        statute_hits = store.query(
            _statute_query(case.charges),
            n_results=settings.rag_top_k_statutes,
            doc_type="statute",
        )
        for h in statute_hits:
            context.append(
                RetrievedContext(
                    statute_id=h["chunk_id"],
                    text=h["text"],
                    relevance=h["relevance"],
                    source="statute",
                )
            )

        precedent_hits = store.query(
            _precedent_query(case),
            n_results=settings.rag_top_k_precedent,
            doc_type="precedent",
        )
        for h in precedent_hits:
            context.append(
                RetrievedContext(
                    statute_id=h["chunk_id"],
                    text=h["text"],
                    relevance=h["relevance"],
                    source="precedent",
                )
            )
    except Exception as exc:  # noqa: BLE001 - retrieval must not kill the run
        # Downgrade to no-context so the Judge still renders a judgment.
        context = []

    return context