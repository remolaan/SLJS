from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from app.config import get_settings
from app.eval.evaluate import evaluate_dataset, evaluate_one
from app.eval.hallucination import check_citations, summarize
from app.eval.store import get_runs_store
from app.graph.session import create_session, get_session
from app.graph.trial import build_graph, run_trial
from app.images import get_image_provider, image_url
from app.images.registry import ALL_PROMPTS
from app.scene import scene_caption
from app.ui.copy import generate_design_copy
from app.models.schemas import (
    CaseInput,
    CaseResult,
    EvaluationReport,
    EvaluationResult,
    HistoricalCase,
    PromptRequest,
    TrialSnapshot,
)
from app.rag.store import get_vectorstore
from app.seed.cases import SEED_CASES
from app.seed.historical import DATASET_NAME, HISTORICAL_DATASET

router = APIRouter(prefix="/api", tags=["trial"])


@router.get("/health")
def api_health() -> dict:
    from app.llm import get_llm

    settings = get_settings()
    return {
        "status": "ok",
        "llm_provider": get_llm(settings).name,
        "rag_enabled": settings.rag_enabled,
    }


@router.get("/seed-case/{key}")
def get_seed_case(key: str) -> CaseInput:
    if key not in SEED_CASES:
        raise HTTPException(status_code=404, detail=f"Unknown seed case: {key}")
    return SEED_CASES[key]()


# --- one-shot (non-stepped) run ----------------------------------------------


@router.post("/cases/run", response_model=CaseResult)
def run_case(case: CaseInput, include_witness: bool = True, witness_name: str = "PW1") -> CaseResult:
    try:
        result = run_trial(case, include_witness=include_witness, witness_name=witness_name)
        store = get_runs_store(get_settings())
        store.save("trial", result.model_dump(mode="json"))
        return result
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Trial failed: {exc}") from exc


# --- stepped / demo trial sessions ------------------------------------------


@router.post("/trials", response_model=TrialSnapshot)
def start_trial(case: CaseInput, include_witness: bool = True, witness_name: str = "PW1") -> TrialSnapshot:
    session = create_session(case, include_witness=include_witness, witness_name=witness_name)
    return session.snapshot()


@router.get("/trials/{trial_id}", response_model=TrialSnapshot)
def trial_state(trial_id: str) -> TrialSnapshot:
    try:
        return get_session(trial_id).snapshot()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/trials/{trial_id}/step", response_model=TrialSnapshot)
def trial_step(trial_id: str) -> TrialSnapshot:
    try:
        return get_session(trial_id).next_step()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Step failed: {exc}") from exc


@router.post("/trials/{trial_id}/ask", response_model=TrialSnapshot)
def trial_ask(
    trial_id: str,
    questioner: str = Body("judge"),
    addressee: str = Body("witness"),
    question: str = Body(...),
    speaker_name: str = Body(""),
) -> TrialSnapshot:
    try:
        return get_session(trial_id).ask(questioner, addressee, question, speaker_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Question failed: {exc}") from exc


# --- hallucination check ------------------------------------------------------


@router.get("/citation-check")
def citation_check_example() -> dict:
    """Example: run a citation-support check on the seed market case."""
    from app.seed.cases import SEED_CASES

    result = run_trial(SEED_CASES["market_altercation"]())
    return {
        "checks": [c.model_dump() for c in result.citation_checks],
        "summary": summarize(result.citation_checks),
    }


# --- evaluation ---------------------------------------------------------------


@router.get("/evaluation/dataset")
def get_dataset() -> dict:
    return {
        "name": DATASET_NAME,
        "cases": [h.model_dump(mode="json") for h in HISTORICAL_DATASET],
    }


@router.post("/evaluation/run-single", response_model=EvaluationResult)
def run_single_eval(historical: HistoricalCase, include_witness: bool = True) -> EvaluationResult:
    result = evaluate_one(historical, get_settings(), include_witness=include_witness)
    store = get_runs_store(get_settings())
    store.save("eval_single", result.model_dump(mode="json"))
    return result


@router.post("/evaluation/run-dataset", response_model=EvaluationReport)
def run_dataset_eval(include_witness: bool = True) -> EvaluationReport:
    report = evaluate_dataset(HISTORICAL_DATASET, get_settings(), dataset_name=DATASET_NAME, include_witness=include_witness)
    store = get_runs_store(get_settings())
    store.save("eval_dataset", report.model_dump(mode="json"))
    return report


# --- graph & store info --------------------------------------------------------


@router.get("/cases/graph")
def graph_schema() -> dict:
    """Expose the compiled LangGraph structure for the frontend."""
    return build_graph().get_graph().to_json()


@router.get("/vectorstore/stats")
def vectorstore_stats() -> dict:
    store = get_vectorstore(get_settings())
    return {"chunks": store.count()}


@router.get("/runs")
def list_runs(kind: str | None = None) -> list[dict]:
    return get_runs_store(get_settings()).list_runs(kind=kind)


# --- image generation ----------------------------------------------------------


@router.post("/images/generate")
def generate_image(req: PromptRequest):
    provider = get_image_provider(get_settings())
    try:
        data_url = provider.generate(req.prompt)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}") from exc
    return {"image": data_url, "provider": provider.name, "stub": provider.is_stub()}


@router.get("/images/manifest")
def image_manifest() -> dict:
    """List all pre-generated static image URLs (zero API calls at runtime).

    Exposes both the raw keys (judgment) and the frontend's prefixed aliases
    (scene_judgment / avatar_judge) so all lookups resolve.
    """
    cache_dir = get_settings().image_cache_dir
    urls = {}
    for name in ALL_PROMPTS:
        url = image_url(name, cache_dir)
        if url:
            urls[name] = url
            # frontend aliases
            if name in ('judge', 'prosecution', 'defense', 'witness', 'intake'):
                urls[f'avatar_{name}'] = url
            else:
                urls[f'scene_{name}'] = url
    return {"images": urls, "count": len(urls)}


# --- UI design copy helper (MiniMax M3 via OpenRouter) --------------------------


@router.post("/ui/design-copy")
def ui_design_copy(req: PromptRequest):
    try:
        return generate_design_copy(req.prompt)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"UI copy failed: {exc}") from exc


# --- live scene narration (MiniMax M3 via OpenRouter) --------------------------


@router.get("/trials/{trial_id}/scene")
def trial_scene(trial_id: str) -> dict:
    try:
        snap = get_session(trial_id).snapshot()
        return scene_caption(snap)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Scene failed: {exc}") from exc