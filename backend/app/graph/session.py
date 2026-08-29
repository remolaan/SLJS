from __future__ import annotations

import uuid

from app.agents import ExaminerAgent
from app.config import Settings, get_settings
from app.eval.hallucination import summarize
from app.eval.store import get_runs_store
from app.graph.trial import build_graph
from app.llm import get_llm
from app.models.schemas import (
    CaseInput,
    Judgment,
    RetrievedContext,
    StructuredCase,
    TranscriptTurn,
    TrialSnapshot,
)

# Display order used by the frontend timeline (labels, not node ids).
STAGE_SEQUENCE = [
    ("intake", "Case Intake"),
    ("prosecution_opening", "Prosecution Opening"),
    ("defense_opening", "Defense Response"),
    ("prosecution_evidence", "Prosecution Evidence"),
    ("witness", "Witness Testimony"),
    ("defense_evidence", "Defense Evidence"),
    ("prosecution_closing", "Prosecution Closing"),
    ("defense_closing", "Defense Closing"),
    ("retrieve", "Law Retrieval (RAG)"),
    ("judge", "Judgment"),
    ("finalize", "Deliberation"),
]


class TrialSession:
    """Drives the LangGraph trial one node at a time for the demo player.

    Uses graph.stream(stream_mode="updates") so each call to next_step()
    executes exactly one node (including its LLM call) and returns the new
    transcript/state. Pausing is simply not calling next_step. Every step is
    persisted to the runs store.
    """

    def __init__(
        self,
        case_input: CaseInput,
        settings: Settings | None = None,
        include_witness: bool = True,
        witness_name: str = "PW1",
    ):
        self.settings = settings or get_settings()
        self.trial_id = uuid.uuid4().hex[:12]
        self.graph = build_graph()
        self.llm = get_llm(self.settings)
        self.case_input = case_input
        self.include_witness = include_witness
        self.witness_name = witness_name if include_witness else ""

        self.steps_done: list[str] = []
        self.transcript: list[TranscriptTurn] = []
        self.case: StructuredCase | None = None
        self.judgment: Judgment | None = None
        self.retrieved_context: list[RetrievedContext] = []
        self.citation_checks = []
        self.result = None
        self.finished = False
        self._dirty = False  # for persistence

        initial = {
            "case_input": case_input,
            "transcript": [],
            "witness_name": self.witness_name,
            "_settings": self.settings,
            "_llm": self.llm,
        }
        self._stream = self.graph.stream(initial, stream_mode="updates")
        self._save()

    # --- public API -------------------------------------------------------
    def next_step(self) -> TrialSnapshot:
        """Execute the next node; returns an updated snapshot."""
        if self.finished:
            return self.snapshot()
        try:
            update = next(self._stream)
        except StopIteration:
            self.finished = True
            self._save()
            return self.snapshot()

        node = list(update.keys())[0]
        out = list(update.values())[0] or {}
        self.steps_done.append(node)
        self._apply_update(node, out)
        self._save()
        return self.snapshot()

    def ask(
        self,
        questioner: str,
        addressee: str,
        question: str,
        speaker_name: str = "",
    ) -> TrialSnapshot:
        """Interactive back-and-forth (e.g., judge asks witness a question)."""
        if self.case is None:
            raise ValueError("Run at least one step (Case Intake) before asking questions.")

        q_speaker = speaker_name or {
            "judge": "The Court",
            "prosecution": "Prosecution",
            "defense": "Defense",
        }.get(questioner, questioner)

        self.transcript.append(
            TranscriptTurn(role=questioner, speaker=q_speaker, label=f"{questioner.title()} question", content=question)
        )

        examiner = ExaminerAgent.for_role(addressee, self.llm)
        answer = examiner.answer(self.case, question, addressee.title())
        self.transcript.append(
            TranscriptTurn(role=addressee, speaker=addressee.title(), label=f"{addressee.title()} answer", content=answer)
        )
        self._save()
        return self.snapshot()

    def snapshot(self) -> TrialSnapshot:
        remaining = [s for s, _ in STAGE_SEQUENCE if s not in self.steps_done]
        current = self.steps_done[-1] if self.steps_done else ""
        label = dict(STAGE_SEQUENCE).get(current, "")
        status = "complete" if self.finished else ("idle" if not self.steps_done else "running")
        return TrialSnapshot(
            trial_id=self.trial_id,
            status=status,
            current_node=current,
            stage_label=label,
            steps_done=list(self.steps_done),
            steps_remaining=remaining,
            transcript=self.transcript,
            case=self.case_input,
            judgment=self.judgment,
            retrieved_context=self.retrieved_context,
            citation_checks=self.citation_checks,
        )

    # --- internals ---------------------------------------------------------
    def _apply_update(self, node: str, out: dict) -> None:
        if "transcript" in out:
            self.transcript.extend(out["transcript"])
        if "case" in out:
            self.case = out["case"]
        if "retrieved_context" in out:
            self.retrieved_context = out["retrieved_context"]
        if "judgment" in out:
            self.judgment = out["judgment"]
        if "result" in out:
            self.result = out["result"]
            self.judgment = out["result"].judgment
            self.citation_checks = out["result"].citation_checks
            self.finished = True

    def _save(self) -> None:
        try:
            snap = self.snapshot()
            store = get_runs_store(self.settings)
            store.save(
                "trial",
                snap.model_dump(mode="json"),
                run_id=self.trial_id,
            )
        except Exception:  # noqa: BLE001 - persistence must not break the demo
            pass


# In-memory registry of live sessions (server process scope).
_SESSIONS: dict[str, TrialSession] = {}


def create_session(
    case_input: CaseInput,
    settings: Settings | None = None,
    include_witness: bool = True,
    witness_name: str = "PW1",
) -> TrialSession:
    session = TrialSession(
        case_input, settings=settings, include_witness=include_witness, witness_name=witness_name
    )
    _SESSIONS[session.trial_id] = session
    return session


def get_session(trial_id: str) -> TrialSession:
    if trial_id not in _SESSIONS:
        raise KeyError(f"No live session for trial {trial_id}")
    return _SESSIONS[trial_id]