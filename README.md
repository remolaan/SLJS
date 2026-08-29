# AI Judge — Courtroom Simulation for Sri Lanka

An **AI-simulated courtroom** for Sri Lanka. A multi-agent LangGraph pipeline
hears a hypothetical case the way a real Sri Lankan court would — prosecution
presents, defense responds, evidence and witness testimony are weighed, and a
"Judge" agent grounds its reasoning in actual Sri Lankan statutes and prior
case law via retrieval-augmented generation (RAG) — then issues a structured,
citation-anchored judgment.

> **⚠️ Research & educational simulation only.** Not a proposal to replace
> judges or automate real sentencing. All cases are hypothetical/anonymized;
> no real persons, pending cases, or litigant identities. Outputs are **not**
> legal opinions.

## Why

Sri Lanka's judiciary is strained: ~1.1M pending cases, prisons at ~4x
capacity with >75% remand, and a contested proposal to raise judicial
retirement ages. This project studies where AI could assist an overloaded
judiciary (triage, drafting, precedent research, decision support) and where
full automation breaks down (rights, bias, accountability, legal-reasoning
limits). See `paper/paper.md` for the research framing and ethics section.

## Architecture

```
Case Intake Agent ──▶ Prosecution ──▶ Defense ──▶ Witness (optional)
      └─▶ Defense evidence ──▶ Closings ──▶ Judge Agent ◀── RAG (Chroma)
                                          └─▶ structured judgment
```

- **Orchestration:** LangGraph state machine (`app/graph/trial.py`)
- **Agents:** one distinct model call + system prompt per role
  (`app/agents/`)
- **RAG:** structure-aware chunking (statutes by section, judgments by
  facts/reasoning/holding) → Chroma vector store → retrieval
  (`app/rag/`)
- **API:** FastAPI (`app/api/`)
- **Frontend:** React + Vite courtroom UI (`frontend/`)

## Sri Lankan legal model

The simulation follows the real structure of the Sri Lankan courts, not a
generic template:

- **Criminal** cases are **State/AG vs Accused** — the victim is a witness, not
  a party. **Civil** cases are **Plaintiff vs Defendant** (private counsel, no
  state). **Appeals** are **Appellant vs Respondent**.
- **Bench size varies by court & severity** and is modelled explicitly —
  Magistrate (1), High Court (1), **Trial-at-Bar (3)**, District (1),
  Court of Appeal (≥3), Supreme Court (3/5/7).
- **Multi-judge benches** run N parallel judge agents then a deliberation /
  voting node that returns a **majority verdict and records dissent**.

Six scenario templates are available (`/api/scenarios`): minor criminal,
serious criminal, trial-at-bar, civil dispute, criminal appeal, and a
constitutional application. See `docs/legal_model.md`.

## Features

- **Live demo player** — step a trial through like a real hearing: Continue /
  Auto-play / Pause, a court timeline, and live chat-bubble transcript.
- **Interactive questions** — the judge (or counsel) can ask the witness or
  opposing counsel a question mid-trial and get a recorded answer.
- **Grounded judgment** — the verdict card shows facts found, legal reasoning,
  citations, sentence, and expandable **supporting sources** (the statute
  paragraph and similar-case precedent the decision relied on).
- **Refusal to convict** — the judge returns `insufficient_evidence` when the
  record does not meet the burden of proof, instead of forcing a verdict.
- **Hallucination / citation check** — every judgment citation is verified
  against the retrieved corpus; unverified citations are flagged.
- **Judge evaluation** — feed historical (anonymized) cases with known outcomes;
  the system predicts a verdict and the dashboard reports accuracy, confidence,
  citation accuracy, hallucination rate, a confusion matrix, and per-case
  breakdowns.
- **Persistence** — every trial, step, question, and evaluation is saved to
  `backend/data/runs/`.

## Setup

Requires Python 3.12+.

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Chroma needs sqlite >= 3.35. This distro ships 3.26; a venv sitecustomize
# swaps in pysqlite3-binary automatically. Install it:
.venv/bin/pip install pysqlite3-binary

# Configure
cp .env.example .env
#   - LLM_PROVIDER=deepseek  (set DEEPSEEK_API_KEY)
#   - or LLM_PROVIDER=stub   (offline demo, no key needed)
```

## Run

```bash
cd backend

# 1. Ingest the legal corpus into Chroma (downloads an embedding model once)
.venv/bin/python ingest_corpus.py

# 2a. Run a seed case from the CLI
.venv/bin/python run_case.py --seed market_altercation
.venv/bin/python run_case.py --seed shophouse_theft --json

# 2b. Or start the API
.venv/bin/python -m uvicorn app.main:app --reload
#   GET  /health
#   GET  /api/vectorstore/stats
#   GET  /api/cases/graph
#   POST /api/cases/run   (body: CaseInput JSON)

# 3. Start the React frontend (separate terminal)
cd ../frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api -> :8000)
```

> **Stub provider:** without a `DEEPSEEK_API_KEY`, the pipeline runs on a
> deterministic offline "stub" so you can verify the state machine, RAG, and
> API end-to-end. Set `LLM_PROVIDER=deepseek` + `DEEPSEEK_API_KEY` for live
> model calls.

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/cases/run` | one-shot full trial |
| POST | `/api/trials` | start a stepped demo session |
| GET | `/api/trials/{id}` | current session state |
| POST | `/api/trials/{id}/step` | execute the next trial stage |
| POST | `/api/trials/{id}/ask` | judge/counsel asks a question |
| GET | `/api/seed-case/{key}` | concrete seed CaseInput |
| GET | `/api/evaluation/dataset` | historical cases with ground truth |
| POST | `/api/evaluation/run-single` | evaluate one historical case |
| POST | `/api/evaluation/run-dataset` | evaluate the full dataset |
| GET | `/api/citation-check` | hallucination/citation-support example |
| GET | `/api/runs` | list saved runs |

## Project layout

```
backend/
  app/
    agents/       # intake, prosecution, defense, witness, closing, judge, examiner
    graph/        # LangGraph state machine, run_trial(), stepped TrialSession
    eval/         # hallucination/citation check, accuracy evaluation, runs store
    llm/          # provider interface (deepseek, stub)
    models/       # Pydantic schemas
    rag/          # chunking, vector store, retrieval
    api/          # FastAPI routes
    seed/         # hypothetical seed cases + historical eval dataset
  data/
    corpus/       # statutes + precedent text (structure-aware chunking)
    vectorstore/  # Chroma persistence
    runs/         # saved trials/evaluations (JSON)
  run_case.py
  ingest_corpus.py
frontend/
  src/
    App.jsx
    api.js
    components/
      LiveTrial.jsx    # demo player: step/continue/ask/timeline/transcript
      JudgmentCard.jsx # verdict + supporting sources + hallucination check
      Evaluation.jsx   # accuracy dashboard + confusion matrix
    styles.css
paper/
  paper.md        # research paper skeleton (methodology, eval, ethics)
```

## Adding legal corpus

Place `.txt` files under `backend/data/corpus/`. Structure matters:

- **Statutes:** start each section with `s.N:` (or `Section N:`).
- **Judgments:** use `Facts:` / `Issues:` / `Reasoning:` / `Held:` headers.
- **Constitution:** start each article with `Article N:`.

Then re-run `ingest_corpus.py` (idempotent by chunk id).

## Disclaimers

- This is not legal advice and outputs are not legal opinions.
- Retrieved law grounds the Judge's reasoning, but models can hallucinate
  citations — every citation should be verified against the source.
- Fact-pattern similarity retrieval is not stare decisis; see `paper/paper.md`.
