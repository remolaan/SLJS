# AI Judge — Backend Workflow & Graph (Mermaid)

This document describes the **backend logic** of AI Judge end to end: the LangGraph
state machine, node-by-node flow, the scenario-aware routing, multi-judge deliberation,
the RAG pipeline, and the verdict model. All diagrams are Mermaid (rendered on GitHub).

> **Status:** research/educational simulation. Not a deployable adjudication system.

---

## 1. Top-level pipeline

```mermaid
flowchart TB
    IN["CaseInput<br/>(charge, facts, evidence,<br/>parties, bench)"] --> INT["Intake Agent<br/>maps charges → Penal Code sections"]
    INT --> CASE["StructuredCase"]
    CASE --> PIPELINE["Scenario-aware trial pipeline"]
    PIPELINE --> RAG["RAG retrieval<br/>(statutes by charge +<br/>precedent by fact-pattern)"]
    RAG --> J["Judge (single or multi-judge bench)"]
    J --> FIN["Finalize<br/>(citation / hallucination check)"]
    FIN --> OUT["CaseResult<br/>(transcript + judgment + checks)"]
```

---

## 2. The LangGraph state machine

The whole trial is a single `StateGraph` in `app/graph/trial.py`. Each node is one
distinct LLM call with its own role system-prompt. `TrialState` is the shared dict.

```mermaid
flowchart LR
    START --> intake
    intake -->|StructuredCase| openingA["opening (claimant side)"]
    openingA --> openingB["response (other side)"]
    openingB --> evidenceA["evidence (claimant side)"]
    evidenceA --> witness
    witness -->|has witness| evidenceB["evidence (other side)"]
    witness -->|no witness| evidenceB
    evidenceB --> closingA["closing (claimant side)"]
    closingA --> closingB["closing (other side)"]
    closingB --> retrieve["RAG retrieve"]
    retrieve --> judge["judge (single) OR bench (N parallel)"]
    judge --> finalize["finalize (citation check)"]
    finalize --> END
```

The transcript channel uses a **reducer** so nodes append, never overwrite:

```python
def _append_turns(existing, update):
    return (existing or []) + (update or [])
```

### `TrialState` fields

| key | type | purpose |
|-----|------|---------|
| `case_input` | `CaseInput` | raw input |
| `case` | `StructuredCase` | intake output |
| `transcript` | `list[TranscriptTurn]` | accumulated, reducer-merged |
| `prosecution_opening` … `defense_closing` | `str` | per-stage outputs |
| `retrieved_context` | `list[RetrievedContext]` | RAG hits for the judge |
| `judgment` | `Judgment` | parsed verdict (+ directive) |
| `bench_judgments` | `list` | per-judge judgments (bench) |
| `result` | `CaseResult` | final envelope + citation checks |
| `_llm`, `_settings` | internal | provider + settings |

---

## 3. Scenario-aware routing (`case_type`)

The node set is chosen by `case_type` and the `bench`. Sri Lanka follows the common-law
model: the **State/AG prosecutes** (victim is a witness, not a party); civil disputes are
private parties; appeals are appellant vs respondent.

```mermaid
flowchart TD
    CT["case_type"] --> CRIM["criminal"]
    CT --> CIV["civil"]
    CT --> APP["appeal"]
    CRIM --> C1["ProsecutionAgent vs DefenseAgent<br/>(State/AG vs Accused)"]
    CIV --> C2["PlaintiffCounselAgent vs DefendantCounselAgent<br/>(private parties, no state)"]
    APP --> C3["AppellantCounselAgent vs RespondentCounselAgent<br/>(briefs, not fresh opening/evidence)"]
```

Routing is centralized in `counsel_for(case_type, side)` (`app/agents/litigants.py`).

### Bench sizes by scenario

```mermaid
flowchart LR
    S1["Minor criminal — Magistrate"] --> B1["1 judge"]
    S2["Serious criminal — High Court"] --> B2["1 judge"]
    S3["Trial-at-Bar / financial — High Court at Bar"] --> B3["3 judges"]
    S4["Civil — District Court"] --> B4["1 judge"]
    S5["Criminal appeal — Court of Appeal"] --> B5["≥ 3 judges"]
    S6["Constitutional / FR — Supreme Court"] --> B6["3 / 5 / 7 judges"]
```

---

## 4. Multi-judge bench deliberation

When `len(bench) > 1`, the single `judge` node becomes **N parallel Judge Agent calls**
(each sees the same transcript + RAG context, differing only by `JudgeProfile`) followed by
a **deliberation / voting node** that returns a **majority verdict** and records dissent.

```mermaid
flowchart TB
    T["transcript + RAG context"]
    T --> J1["Judge 1 (JudgeProfile J1)"]
    T --> J2["Judge 2 (JudgeProfile J2)"]
    T --> J3["Judge 3 (JudgeProfile J3)"]
    J1 --> V["deliberation / voting<br/>(majority verdict + dissents)"]
    J2 --> V
    J3 --> V
    V --> OUT["BenchVerdict<br/>(majority, per_judge, dissents)"]
```

`_aggregate_bench` tallies per-judge verdicts, picks the majority, and records which
judges dissented. The `evidentiary_directive` is aggregated by most-common non-empty value.

---

## 5. Verdict model (binary + directive)

Verdicts are **binary** — `guilty`/`not_guilty` (or `liable`/`not_liable`). There is no
`insufficient_evidence`. When the record is insufficient the judge returns `not_guilty`
plus an `evidentiary_directive`:

```mermaid
flowchart TD
    Q["Can the elements be proved to the<br/>applicable burden of proof?"]
    Q -->|Yes| GUILTY["verdict: guilty / liable"]
    Q -->|No - gap could be remedied| PM["verdict: not_guilty<br/>evidentiary_directive: produce_more<br/>release: false"]
    Q -->|No - case should end| ACQ["verdict: not_guilty<br/>evidentiary_directive: acquit<br/>release: true"]
```

The parser normalises any legacy `insufficient_evidence` to `not_guilty + produce_more`.

---

## 6. RAG pipeline

```mermaid
flowchart LR
    CORPUS["Legal corpus (.txt)<br/>Penal Code · CPC Act · Evidence Ordinance ·<br/>Constitution · precedent"] --> CHUNK["Structure-aware chunking"]
    CHUNK --> CHROM["Chroma vector store<br/>(cosine, idempotent by chunk-hash)"]
    CHARGES["charges"] --> Q1["statute query"]
    FACTS["facts"] --> Q2["precedent query (fact-pattern)"]
    Q1 --> RETR["retrieve_for_judge"]
    Q2 --> RETR
    CHROM --> RETR
    RETR --> CTX["RetrievedContext[] → judge prompt"]
```

- **Chunking:** statutes by `s.N:`; judgments by `Facts/Issues/Reasoning/Held`; constitution
  by `Article N:`.
- **Retrieval:** statutes keyed to the charge (`CHARGE_HINTS`), precedent by fact similarity.
- **Limitation:** fact-pattern similarity ≠ stare decisis (ratio decidendi).

---

## 7. Stepped "live hearing" loop

The demo player runs the same graph one node at a time using LangGraph
`stream(stream_mode="updates")` (`app/graph/session.py`). Pausing = not calling
`next_step()`; each step persists to `data/runs/`.

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as FastAPI /api/trials
    participant S as TrialSession
    participant G as LangGraph stream
    FE->>API: POST /trials (CaseInput)
    API->>S: create_session()
    S->>G: graph.stream(initial)
    API-->>FE: TrialSnapshot (idle)
    loop until complete
        FE->>API: POST /trials/{id}/step
        API->>S: next_step()
        S->>G: next(stream) → one node
        S->>S: apply update, persist
        API-->>FE: TrialSnapshot (transcript)
    end
    FE->>API: POST /trials/{id}/ask (interrupt/question)
    API->>S: ask() → ExaminerAgent
    API-->>FE: TrialSnapshot
```

---

## 8. LLM provider selection

```mermaid
flowchart TD
    K["keys present?"]
    K -->|"deepseek_api_key"| D["DeepSeekProvider"]
    K -->|"openrouter_api_key"| O["OpenRouterProvider (free models, rotate on rate-limit)"]
    K -->|none| S["StubProvider (offline demo)"]
```

Free-model rotation in `OpenRouterProvider.complete()` tries each model in `free_models`
until one responds (handles per-model daily rate limits).

---

## 9. Evaluation & correctness

```mermaid
flowchart LR
    HIST["HistoricalCase (anonymized,<br/>ground-truth verdict)"] --> EVAL["evaluate_one"]
    EVAL --> COMPARE["predicted vs ground-truth"]
    COMPARE --> REPORT["EvaluationReport<br/>(accuracy, confidence, hallucination rate, confusion)"]
    HIST --> BENCH["bench_consistency<br/>(single vs 3-judge on same case)"]
    JUDG["Judgment"] --> HC["check_citations (hallucination)"]
    HC --> CIT["CitationCheck[] + summary"]
```

---

## 10. API surface (`app/api/routes.py`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | health + active LLM provider |
| GET | `/api/scenarios` | list Sri Lankan scenario templates |
| GET | `/api/scenario/{key}` | concrete scenario `CaseInput` |
| GET | `/api/seed-case/{key}` | legacy seed case |
| POST | `/api/cases/run` | one-shot full trial |
| POST | `/api/trials` | start stepped session |
| GET | `/api/trials/{id}` | session state |
| POST | `/api/trials/{id}/step` | execute next node |
| POST | `/api/trials/{id}/ask` | judge/counsel asks a question |
| GET | `/api/trials/{id}/scene` | scene narration |
| GET | `/api/images/manifest` | pre-generated static image URLs |
| GET | `/api/evaluation/dataset` | historical cases with ground truth |
| POST | `/api/evaluation/run-single` | evaluate one historical case |
| POST | `/api/evaluation/run-dataset` | evaluate the dataset |
| POST | `/api/evaluation/bench-consistency` | single vs multi-judge comparison |
| GET | `/api/cases/graph` | compiled LangGraph JSON |
| GET | `/api/vectorstore/stats` | chunk count |
| GET | `/api/runs` | saved runs |
