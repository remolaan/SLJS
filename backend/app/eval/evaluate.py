from __future__ import annotations

from app.config import Settings
from app.eval.hallucination import summarize
from app.graph.trial import run_trial
from app.models.schemas import (
    EvaluationReport,
    EvaluationResult,
    HistoricalCase,
)


def evaluate_one(
    historical: HistoricalCase,
    settings: Settings,
    include_witness: bool = True,
) -> EvaluationResult:
    """Run an AI trial on a historical case and compare with ground truth."""
    result = run_trial(historical.case, settings=settings, include_witness=include_witness)
    judgment = result.judgment
    predicted = judgment.verdict if judgment else "insufficient_evidence"
    correct = predicted == historical.ground_truth_verdict
    cit_summary = summarize(result.citation_checks)
    return EvaluationResult(
        case_title=historical.case.title,
        predicted_verdict=predicted,
        ground_truth_verdict=historical.ground_truth_verdict,
        correct=correct,
        verdict_confidence=judgment.verdict_confidence if judgment else 0.0,
        citation_accuracy=cit_summary["citation_accuracy"],
        hallucinated_citations=cit_summary["hallucinated"],
        total_citations=cit_summary["total_citations"],
        notes=historical.notes,
        judgment=judgment,
    )


def evaluate_dataset(
    cases: list[HistoricalCase],
    settings: Settings,
    dataset_name: str = "",
    include_witness: bool = True,
) -> EvaluationReport:
    results = [evaluate_one(c, settings, include_witness=include_witness) for c in cases]

    n = len(results)
    correct = sum(1 for r in results if r.correct)
    accuracy = round(correct / n, 4) if n else 0.0
    mean_conf = round(
        sum(r.verdict_confidence for r in results) / n, 4
    ) if n else 0.0
    mean_cit = round(
        sum(r.citation_accuracy for r in results) / n, 4
    ) if n else 1.0
    total_cits = sum(r.total_citations for r in results)
    hallucinated = sum(len(r.hallucinated_citations) for r in results)
    hallucination_rate = round(hallucinated / total_cits, 4) if total_cits else 0.0

    confusion: dict[str, dict[str, int]] = {}
    for r in results:
        row = confusion.setdefault(r.ground_truth_verdict, {})
        row[r.predicted_verdict] = row.get(r.predicted_verdict, 0) + 1

    return EvaluationReport(
        dataset_name=dataset_name,
        n_cases=n,
        correct=correct,
        accuracy=accuracy,
        mean_confidence=mean_conf,
        mean_citation_accuracy=mean_cit,
        hallucination_rate=hallucination_rate,
        results=results,
        confusion=confusion,
    )