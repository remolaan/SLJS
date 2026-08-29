# AI Judge — System Architecture

This document explains how the AI Judge courtroom simulation actually works end to end: the
LangGraph state machine, each agent node, the RAG pipeline, the stepped "live hearing" loop, the
LLM layer, and the frontend. It is the technical companion to `legal_model.md` (which describes
the Sri Lankan legal corrections) and `paper/paper.md` (the research framing).

> **Status:** research/educational simulation. Not a deployable adjudication system.

---

## 1. Big picture

```
User / seeded scenario
        │  CaseInput (charge, facts, evidence, parties)
        ▼
┌────────────────────────────────────────────────────────────┐
│              LangGraph state machine (TrialState)          │
│                                                            │
│  intake → prosecution/plaintiff → defense/defendant →      │
│  evidence → witness → closings → RAG retrieve →            │
│  judge (single or multi-judge bench) → finalize            │
└────────────────────────────────────────────────────────────┘
        │
        ▼
   Structured judgment (facts, reasoning, citations, verdict, sentence)
```

The whole pipeline is a **single LangGraph `StateGraph`** (`app/graph/trial.py`). Each node is a
**distinct LLM call** with its own role-specific system prompt — not one model "wearing hats" —
which keeps reasoning separable and auditable.

---

## 2. The shared state: `TrialState`

Defined as a `TypedDict` in `app/graph/trial.py`:

| key | type | notes |
|-----|------|-------|
| `case_input` | `CaseInput` | the raw input case |
| `case` | `StructuredCase` | the case file after the Intake agent maps charges → sections |
| `transcript` | `list[TranscriptTurn]` | accumulated turns; merged with the `_append_turns` **reducer** |
| `prosecution_opening`, `defense_opening`, … | `str` | per-stage outputs (kept for reference) |
| `retrieved_context` | `list[RetrievedContext]` | RAG hits handed to the judge |
| `judgment` | `Judgment` | the parsed structured judgment |
| `result` | `CaseResult` | the final envelope incl. citation checks |
| `_llm`, `_settings` | internal | injected provider + settings |

The transcript uses a **channel reducer** so each node *appends* its turns instead of overwriting:

```python
def _append_turns(existing, update):
    return (existing or []) + (update or [])
```

---

## 3. The node sequence (current linear chain)

```
START
 └─ intake
     └─ prosecution_opening
         └─ defense_opening
             └─ prosecution_evidence
                 └─ witness          (conditional: skipped if no witness_name)
                     └─ defense_evidence
                         └─ prosecution_closing
                             └─ defense_closing
                                 └─ retrieve  (RAG)
                                     └─ judge
                                         └─ finalize  (citation check)
                                             └─ END
```

```mermaid
flowchart LR
    START --> intake
    intake --> prosecution_opening
    prosecution_opening --> defense_opening
    defense_opening --> prosecution_evidence
    prosecution_evidence --> witness
    witness -->|has witness| defense_evidence
    witness -->|no witness| defense_evidence
    defense_evidence --> prosecution_closing
    prosecution_closing --> defense_closing
    defense_closing --> retrieve
    retrieve --> judge
    judge --> finalize
    finalize --> END
```

**Note on the legal-model rework:** after the corrections in `legal_model.md`, this linear chain is
parameterized by `case_type` and `bench` — the "prosecution/defense" nodes become plaintiff/defendant
or appellant/respondent, and a multi-judge bench runs N parallel judge nodes followed by a
deliberation/voting node.

---

## 4. Agent nodes (`app/agents/`)

Each node instantiates an agent with its own system prompt and runs one LLM call.

| agent | system-prompt role | returns |
|-------|--------------------|---------|
| `IntakeAgent` | Case Intake Officer — maps charges to Penal Code sections | structured JSON (`mapped_offences`, `intake_notes`) → `StructuredCase` |
| `ProsecutionAgent` | State Counsel — opening, evidence, aggravating precedent | prose |
| `DefenseAgent` | Defense Counsel — response, mitigation, procedural challenges | prose |
| `WitnessAgent` | Witness/Victim — testimony consistent with facts | prose |
| `ClosingAgent` | delivers closing for a given side | prose |
| `JudgeAgent` | Judge — weighs both sides, applies burden of proof, returns structured JSON | `Judgment` (parsed) |
| `ExaminerAgent` | interactive Q&A (judge/counsel ask witness or counsel) | prose |

The Judge agent is instructed **not to force a verdict** and verdicts are **binary**
(`guilty`/`not_guilty`, or `liable`/`not_liable` in civil). There is no
`insufficient_evidence` verdict. If the record does not establish the elements to the
applicable burden of proof, the judge instead sets `verdict: "not_guilty"` and an
**`evidentiary_directive`**:

- `produce_more` — the prosecution/plaintiff could still remedy the gap; the court directs
  that further evidence be produced (`release: false`).
- `acquit` — the case should simply end; the accused is acquitted (`release: true`).

It returns strict JSON:

```json
{
  "facts_found": "...",
  "legal_reasoning": "...",
  "citations": ["..."],
  "verdict": "guilty|not_guilty|liable|not_liable",
  "verdict_confidence": 0.0,
  "evidentiary_directive": "" | "produce_more" | "acquit",
  "sentence": { "custodial": false, "term_years": null, ... },
  "release": false,
  "dissent_notes": "..."
}
```

---

## 5. RAG pipeline (`app/rag/`)

- **Structure-aware chunking** (`chunking.py`): statutes split by section (`s.N:`), judgments by
  `Facts/Issues/Reasoning/Held`, the constitution by `Article N:` — not fixed token windows.
- **Vector store** (`store.py`): Chroma (PersistentClient), cosine, idempotent ingestion keyed by
  chunk-id hash.
- **Retrieval** (`retrieval.py`): the judge receives
  - **statutes** retrieved from the charges (`_statute_query`, with `CHARGE_HINTS` keyword mapping),
  - **precedent** retrieved by fact-pattern similarity (`_precedent_query`).
- Results are wrapped as `RetrievedContext` and injected into the Judge's prompt with inline
  citations.

> **Documented limitation:** fact-pattern similarity retrieval is **not** stare decisis — precedent
> turns on *ratio decidendi*, not surface similarity. This is flagged in the paper.

---

## 6. The stepped "live hearing" loop (`app/graph/session.py`)

The demo player runs the same graph one node at a time:

- `TrialSession.__init__` builds the graph and opens `graph.stream(initial, stream_mode="updates")`.
- Each `next_step()` pulls the **next node's update** from the stream (one LLM call), applies it to
  the session's copy of the state, and returns a `TrialSnapshot` (transcript, current stage,
  steps done/remaining, judgment if any).
- **Pausing is simply not calling `next_step()`.** Every step is persisted to `data/runs/`.
- The frontend polls `/api/trials/{id}/step`; the snapshot is also cached in `localStorage` so the
  trial survives tab switches / reloads.

The API surface (`app/api/routes.py`): `POST /api/trials`, `GET|POST /api/trials/{id}`,
`POST /api/trials/{id}/step`, `POST /api/trials/{id}/ask`, `GET /api/trials/{id}/scene`,
`GET /api/images/manifest`, evaluation + citation-check endpoints, and `POST /api/images/generate`.

---

## 7. LLM layer (`app/llm/`)

- `LLMProvider` — minimal chat interface (system + user → text).
- `DeepSeekProvider` — DeepSeek via OpenAI-compatible API.
- `OpenRouterProvider` — any OpenRouter model, used for free models; **rotates across `free_models`**
  on rate-limit so the trial keeps running.
- `StubProvider` — deterministic offline placeholder so the pipeline runs with no key.
- `get_llm(settings)` picks the provider: DeepSeek if a key is present, else free OpenRouter, else stub.

---

## 8. Frontend (`frontend/src/`)

- **`LiveTrial.jsx`** — 1/3 interactive chat: streaming typewriter reveal, you-as-participant
  (right-aligned "You" bubbles), text-to-speech (browser `speechSynthesis`, 🔊/🔇 toggle), Pause /
  Continue / Autoplay with in-flight-step cancellation on pause.
- **`SceneVisualizer.jsx`** — 2/3 live scene image + active-speaker avatar overlay + reference cards.
- **`SpotlightBar.jsx`** — sticky strip: pulsing avatar + MiniMax narration of the current speaker.
- **`Judgment.jsx` / `JudgmentCard.jsx`** — the full judgment (verdict, reasoning, citations,
  supporting sources, hallucination check).
- **`Evaluation.jsx`** — accuracy dashboard (confusion matrix, hallucination rate, per-case breakdown).
- Images are **pre-generated** static SVG served from `/static/images/*.svg` (proxied through Vite),
  listed by `/api/images/manifest`.

---

## 9. Evaluation & correctness (`app/eval/`)

- `hallucination.py` — verifies each judgment citation against the retrieved corpus; flags
  unsupported ones as possible hallucinations.
- `evaluate.py` — runs historical (anonymized) cases, compares predicted vs ground-truth verdicts,
  computes accuracy, mean confidence, citation accuracy, hallucination rate, confusion matrix.
- `store.py` — JSON persistence of trials and evaluation runs to `data/runs/`.
