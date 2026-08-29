from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents import (
    ClosingAgent,
    DefenseAgent,
    IntakeAgent,
    JudgeAgent,
    ProsecutionAgent,
    WitnessAgent,
)
from app.config import Settings, get_settings
from app.models.schemas import (
    CaseInput,
    CaseResult,
    Judgment,
    RetrievedContext,
    StructuredCase,
    TranscriptTurn,
)
from app.rag.retrieval import retrieve_for_judge


def _append_turns(existing: list[TranscriptTurn] | None, update: list[TranscriptTurn] | None) -> list[TranscriptTurn]:
    """Reducer: accumulate transcript turns across nodes."""
    return (existing or []) + (update or [])


class TrialState(TypedDict, total=False):
    case_input: CaseInput
    case: StructuredCase
    transcript: Annotated[list[TranscriptTurn], _append_turns]
    prosecution_opening: str
    defense_opening: str
    prosecution_evidence: str
    defense_evidence: str
    witness_name: str
    witness_testimony: str
    prosecution_closing: str
    defense_closing: str
    retrieved_context: list[RetrievedContext]
    judgment: Judgment
    result: CaseResult
    _llm: object
    _settings: Settings


def _emit(role: str, content: str, label: str = "", speaker: str = "") -> TranscriptTurn:
    return TranscriptTurn(role=role, speaker=speaker or label, label=label, content=content)


# --- node implementations -----------------------------------------------------


def intake_node(state: TrialState) -> dict:
    agent = IntakeAgent(state["_llm"])
    case = agent.process(state["case_input"])
    turn = _emit("intake", f"Mapped offences: {case.mapped_offences}\nNotes: {case.intake_notes}", label="Case Intake")
    return {"case": case, "transcript": [turn]}


def prosecution_opening_node(state: TrialState) -> dict:
    agent = ProsecutionAgent(state["_llm"])
    text = agent.opening(state["case"])
    return {"prosecution_opening": text, "transcript": [_emit("prosecution", text, label="Prosecution Opening")]}


def defense_opening_node(state: TrialState) -> dict:
    agent = DefenseAgent(state["_llm"])
    text = agent.opening(state["case"], state.get("prosecution_opening", ""))
    return {"defense_opening": text, "transcript": [_emit("defense", text, label="Defense Response")]}


def prosecution_evidence_node(state: TrialState) -> dict:
    agent = ProsecutionAgent(state["_llm"])
    text = agent.evidence(state["case"])
    return {"prosecution_evidence": text, "transcript": [_emit("prosecution", text, label="Prosecution Evidence")]}


def witness_node(state: TrialState) -> dict:
    agent = WitnessAgent(state["_llm"])
    name = state.get("witness_name") or "PW1"
    text = agent.testify(state["case"], name)
    return {"witness_testimony": text, "transcript": [_emit("witness", text, label=f"Witness: {name}", speaker=name)]}


def defense_evidence_node(state: TrialState) -> dict:
    agent = DefenseAgent(state["_llm"])
    text = agent.evidence(state["case"])
    return {"defense_evidence": text, "transcript": [_emit("defense", text, label="Defense Evidence")]}


def prosecution_closing_node(state: TrialState) -> dict:
    agent = ClosingAgent(state["_llm"])
    so_far = "\n".join(t.content for t in state["transcript"])
    text = agent.for_side("prosecution", state["case"], so_far)
    return {"prosecution_closing": text, "transcript": [_emit("prosecution", text, label="Prosecution Closing")]}


def defense_closing_node(state: TrialState) -> dict:
    agent = ClosingAgent(state["_llm"])
    so_far = "\n".join(t.content for t in state["transcript"])
    text = agent.for_side("defense", state["case"], so_far)
    return {"defense_closing": text, "transcript": [_emit("defense", text, label="Defense Closing")]}


def retrieve_node(state: TrialState) -> dict:
    settings = state.get("_settings")
    if settings and settings.rag_enabled:
        context = retrieve_for_judge(state["case"], settings)
    else:
        context = []
    return {"retrieved_context": context}


def judge_node(state: TrialState) -> dict:
    settings = state.get("_settings")
    agent = JudgeAgent(state["_llm"])
    raw = agent.judge(state["case"], state["transcript"], state.get("retrieved_context", []))
    judgment = _parse_judgment(raw)
    turn = _emit(
        "judge",
        f"VERDICT: {judgment.verdict}\n{judgment.legal_reasoning}\nCitations: {judgment.citations}",
        label="Judgment",
        speaker="The Court",
    )
    return {"judgment": judgment, "transcript": [turn]}


def _parse_judgment(raw: str) -> Judgment:
    import json
    import re

    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0)) if m else json.loads(raw)
        sent = data.get("sentence") or {}
        sentence = None
        if sent:
            from app.models.schemas import Sentence

            sentence = Sentence(
                custodial=bool(sent.get("custodial", False)),
                term_years=sent.get("term_years"),
                term_months=sent.get("term_months"),
                fine_lkr=sent.get("fine_lkr"),
                conditions=sent.get("conditions", []),
                note=sent.get("note", ""),
            )
        verdict = data.get("verdict", "not_guilty")
        return Judgment(
            facts_found=data.get("facts_found", ""),
            legal_reasoning=data.get("legal_reasoning", ""),
            citations=data.get("citations", []),
            verdict=verdict,
            verdict_confidence=float(data.get("verdict_confidence", 0.0)),
            insufficient_evidence=bool(
                data.get("insufficient_evidence", False)
                or verdict == "insufficient_evidence"
            ),
            sentence=sentence,
            release=bool(data.get("release", False)),
            dissent_notes=data.get("dissent_notes", ""),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return Judgment(
            facts_found="",
            legal_reasoning=raw,
            citations=[],
            verdict="not_guilty",
            release=False,
        )


def finalize_node(state: TrialState) -> dict:
    from app.eval.hallucination import check_citations

    judgment = state.get("judgment")
    checks = check_citations(judgment, state.get("retrieved_context", []))
    result = CaseResult(
        case_title=state["case"].title,
        transcript=state["transcript"],
        retrieved_context=state.get("retrieved_context", []),
        judgment=judgment,
        citation_checks=checks,
        status="complete",
    )
    return {"result": result}


def _conditional_include_witness(state: TrialState) -> str:
    return "witness" if state.get("witness_name") else "skip_witness"


def build_graph(checkpointer=None):
    g = StateGraph(TrialState)

    g.add_node("intake", intake_node)
    g.add_node("prosecution_opening", prosecution_opening_node)
    g.add_node("defense_opening", defense_opening_node)
    g.add_node("prosecution_evidence", prosecution_evidence_node)
    g.add_node("witness", witness_node)
    g.add_node("defense_evidence", defense_evidence_node)
    g.add_node("prosecution_closing", prosecution_closing_node)
    g.add_node("defense_closing", defense_closing_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("judge", judge_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "intake")
    g.add_edge("intake", "prosecution_opening")
    g.add_edge("prosecution_opening", "defense_opening")
    g.add_edge("defense_opening", "prosecution_evidence")
    g.add_edge("prosecution_evidence", "witness")
    g.add_conditional_edges(
        "witness",
        _conditional_include_witness,
        {"witness": "defense_evidence", "skip_witness": "defense_evidence"},
    )
    g.add_edge("defense_evidence", "prosecution_closing")
    g.add_edge("prosecution_closing", "defense_closing")
    g.add_edge("defense_closing", "retrieve")
    g.add_edge("retrieve", "judge")
    g.add_edge("judge", "finalize")
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer)


def run_trial(
    case_input: CaseInput,
    settings: Settings | None = None,
    include_witness: bool = True,
    witness_name: str = "PW1",
) -> CaseResult:
    settings = settings or get_settings()
    from app.llm import get_llm

    graph = build_graph()
    initial: TrialState = {
        "case_input": case_input,
        "transcript": [],
        "witness_name": witness_name if include_witness else "",
        "_settings": settings,
        "_llm": get_llm(settings),
    }
    final = graph.invoke(initial)
    return final["result"]
