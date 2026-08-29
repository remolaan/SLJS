# AI-Judge: An AI-Simulated Courtroom for Sri Lanka

**Working title:** *AI-Judge: A Multi-Agent Simulation of Adjudication Grounded in
Sri Lankan Law — A Research and Educational Instrument*

> **Status:** Research/educational simulation. This project does **not** propose
> replacing judges or automating real sentencing. All case scenarios are
> hypothetical or anonymized; no real persons, real pending cases, or real
> litigant identities are used.

---

## Abstract

(To be completed after evaluation results.)

Sri Lanka's judiciary is under extreme structural strain: roughly 1.1 million
pending cases, prisons at ~4x capacity with over 75% of inmates on remand,
and a contested legislative proposal to raise judicial retirement ages.
This paper presents **AI-Judge**, a multi-agent simulation that hears a case the
way a Sri Lankan court would — prosecution and defense present, evidence and
testimony are weighed, and a "judge" grounds its reasoning in actual Sri Lankan
statutes and prior case law retrieved via retrieval-augmented generation (RAG) —
and outputs a structured judgment. We evaluate its citation accuracy, reasoning
quality, and consistency, and we document frankly where automated adjudication
breaks down.

---

## 1. Introduction & Motivation

- Justice-system strain: ~1.1M pending cases; ~41,000 inmates vs ~11,000 capacity
  (≈4x); >75% remand; Negombo (Jul 2026, ~28 deaths), Colombo and Kuruwita
  (Aug 2026) riots.
- Root-cause chain: too few judges + slow processing → backlog → long pre-trial
  detention → overcrowding → violence.
- The 22nd Amendment proposal (SC 65→67, CoA 63→65, HC 61→63, District/Magistrate
  60→62) is contested by the Bar Association of Sri Lanka on
  judicial-independence grounds.
- This project studies where AI could *assist* (triage, drafting, precedent
  research, decision support) vs. where full automation fails (rights, bias,
  accountability, legal reasoning limits).
- Explicitly a research/educational simulation — not a proposal to replace judges.

---

## 2. Problem Statement & Related Work

- Formalize the problem: what can an AI courtroom demonstrate about the
  judge-shortage bottleneck?
- Related work: prior AI legal-judgment prediction (e.g., LawGLM, LexGLUE, early
  Chinese and Indian prediction models), the limits of prediction vs.
  adjudication, RAG for legal QA, and the legal ethics literature on automation
  and due process.
- (Expand with citations.)

---

## 3. System Design & Methodology

### 3.1 Multi-agent pipeline (state machine)

Each agent is a distinct model call with its own system prompt and role
constraints (not one model "wearing hats"), keeping reasoning separable and
auditable:

1. **Case Intake Agent** — structures raw input; maps charges to Penal Code /
   statute sections.
2. **Prosecution Agent** — opening, evidence presentation, aggravating precedent.
3. **Defense Agent** — response, mitigating factors, procedural challenges,
   favorable precedent.
4. **Witness/Victim Agent** *(optional)* — testimony consistent with case facts;
   cross-examination.
5. **Closing Arguments** — prosecution and defense.
6. **Judge Agent** — retrieves statute sections + precedent via RAG, applies the
   burden of proof, issues a structured judgment with inline citations.

The pipeline is implemented as a LangGraph state machine. *See
`backend/app/graph/trial.py` for the canonical node order.*

### 3.1.1 Jurisdictional fidelity (Sri Lankan legal model)

The simulation is parameterized to reflect the real structure of the Sri Lankan
courts, rather than a single generic trial template:

- **Criminal cases** follow the common-law model: the **State / Attorney General
  prosecutes**, not the victim. For serious (indictable) offences the AG's
  Department prosecutes in the High Court; police prosecute only minor offences
  in the Magistrate's Court. The **victim is a witness**, not a party with their
  own counsel.
- **Civil disputes** are between two private parties (plaintiff vs defendant),
  each with their own lawyer; no state and no police.
- **Appeals** (Court of Appeal / Supreme Court) run as appellant vs respondent,
  with argument briefs rather than a fresh opening and evidence.

**Bench size varies by court and case severity** and is modelled explicitly:

| Scenario | Court | Bench |
|----------|-------|-------|
| Minor criminal | Magistrate's Court | 1 |
| Serious criminal | High Court (ordinary) | 1 |
| High-profile / financial (Trial-at-Bar) | High Court at Bar | 3 |
| Civil dispute | District Court | 1 |
| Criminal appeal | Court of Appeal | ≥ 3 |
| Constitutional / FR application | Supreme Court | 3 / 5 / 7 |

For multi-judge benches the single `judge` node becomes **N parallel Judge Agent
calls** (each seeing the same transcript and RAG context) followed by a
**deliberation / voting node** that aggregates a majority verdict and records
dissent. This is a distinct research angle: it lets us study whether and how
**multi-judge deliberation differs from single-judge output** — an empirical
question that falls naturally out of modelling the jurisdiction correctly.

*See `docs/legal_model.md` for the full corrections and `docs/architecture.md`
for the implementation.*

### 3.2 RAG pipeline

- **Corpus:** Constitution of Sri Lanka; Penal Code (No. 2 of 1883, as amended);
  Code of Criminal Procedure Act; Evidence Ordinance; Bail Act; and a corpus of
  past judgments (SC, CoA, HC) from public Sri Lankan sources. Licensing/scraping
  terms must be checked before bulk collection.
- **Structure-aware chunking:** statutes by section; judgments by
  facts/issues/reasoning/holding (not fixed token windows). *See
  `backend/app/rag/chunking.py`.*
- **Embeddings:** multilingual-capable model (config: `BAAI/bge-m3`).
- **Vector store:** Chroma. *See `backend/app/rag/store.py`.*
- **Retrieval:** statutes keyed to the charges, top-k precedent by fact-pattern
  similarity. *See `backend/app/rag/retrieval.py`.*

**Documented limitation (required):** fact-pattern similarity retrieval is *not*
legal precedent under stare decisis, which turns on *ratio decidendi* (the legal
principle), not surface similarity. This is a core methodological caveat and a
key finding about the limits of RAG-based adjudication.

### 3.3 Web app

- Backend: Python FastAPI orchestrating agents + RAG. *See `backend/app/api/`.*
- Frontend: React courtroom UI (`frontend/`) with two main views:
  - **Live Trial demo player** — step a trial through like a real hearing
    (Continue / Auto-play / Pause), a court timeline, a live chat-bubble
    transcript, and interactive judge/counsel questions to witnesses or
    opposing counsel.
  - **Judge Evaluation dashboard** — run historical (anonymized) cases and see
    accuracy, confidence, citation accuracy, hallucination rate, a confusion
    matrix, and per-case breakdowns.
- Vector DB: Chroma. LLM: configurable, default DeepSeek.

### 3.4 Step-wise execution & interactivity

The demo executes the LangGraph trial one node at a time
(`backend/app/graph/session.py`) so the entire hearing can be presented live:
prosecution speaks → defense responds → evidence → witness → closings → judge.
Pausing is simply stopping between steps; the full state (transcript, current
stage, retrieved law, judgment) is persisted to `backend/data/runs/` after every
step, satisfying the requirement that everything is saved. The judge may also
interactively ask a witness or counsel a question, and the answer is recorded
onto the record before deliberation.

### 3.5 Refusal to convict (insufficient evidence)

The Judge agent is instructed **not** to force a verdict. Where the record does
not establish the elements of the charge to the applicable burden of proof
(e.g., no admissible evidence covering a required element, absent eyewitnesses,
uncorroborated allegations), it must return a verdict of `insufficient_evidence`
and state which element is unproven. This models the judicial duty to acquit or
decline to adjudicate rather than to fabricate a finding — a key guard against
the failure mode of always producing a conviction.

### 3.6 Hallucination / citation verification

Every citation in a judgment is automatically verified against the retrieved
corpus (`backend/app/eval/hallucination.py`). A citation is flagged *supported*
only if it matches retrieved statute/precedent text (with progressive
case-name/section matching); otherwise it is flagged as a possible
hallucination. This yields per-case citation accuracy and a hallucination rate
reported in the evaluation dashboard.

---

## 4. Evaluation Plan

1. **Comparison against real anonymized outcomes** — where available, compare
   AI verdicts/sentences to actual case outcomes. A working dataset of
   anonymized/hypothetical cases with known ground-truth verdicts ships in
   `backend/app/seed/historical.py`; `run-dataset` computes an accuracy score,
   a confusion matrix, and a hallucination rate end-to-end.
2. **Expert / practitioner review** — law students or practitioners rate
   reasoning quality, citation accuracy, and consistency.
3. **Failure-mode tracking** — hallucinated citations, missed statutory elements,
   inconsistent sentencing across similar fact patterns, and *forced verdicts*
   (cases where the record was insufficient but a verdict was still issued).
4. **Bias check** — run matched scenarios varying only demographic/socioeconomic
   details of the accused and check for disparate outputs.

**Metrics to record (add results tables later):** citation precision/recall,
element-completeness, verdict accuracy vs. ground truth, sentence consistency,
demographic parity, refusal-to-convict correctness, and hallucination rate.

---

## 5. Results

*(Pending. Structure reserved for tables and analysis.)*

---

## 6. Discussion

- What the simulation can legitimately assist with (triage, drafting, precedent
  research, decision support).
- Where it breaks down: due process, accountability, appeal rights, bias,
  and the fact that precedent is *ratio* not similarity.
- The parallel to the real retirement-age debate: experience and human judgment
  in judging are precisely what critics argue cannot be shortcut. This frames
  the discussion of what "assistance" can and cannot substitute for.

---

## 7. Ethics & Limitations (Required)

- **Plain statement:** this is a research/educational simulation, **not** a
  deployable adjudication system.
- No real individuals, real pending cases, or real litigant identities are used;
  all scenarios are hypothetical or anonymized.
- Full automated sentencing raises due-process, accountability, and
  appeal-rights questions that this project does **not** resolve — the authors
  state this directly.
- Retrieved law is used to ground reasoning, but the model may hallucinate
  citations; outputs are not legal opinions and must not be relied upon.
- Mirror the retirement-age debate: human judgment and experience are the very
  attributes critics argue cannot be automated; this project is offered as an
  aid and object of study, not a substitute.

---

## 8. Conclusion

*(To be completed.)*

---

## Appendix A: Reproducibility

- Corpus ingestion: `python ingest_corpus.py`
- Run a seed case: `python run_case.py --seed market_altercation`
- Run a case through the API: `POST /api/cases/run`
- Configuration: `backend/.env` (see `.env.example`).

## Appendix B: Anonymization Policy

- All names in seed cases are explicit pseudonyms.
- No scenario references a real living person, real pending case, or real
  litigant.
