# AI Judge — Sri Lankan Legal Model & Corrections

This document records the corrections to the simulation so it reflects the real structure of the
Sri Lankan legal system. It is the companion to `architecture.md` and `paper/paper.md`.

> All cases are hypothetical/anonymized. Nothing here is legal advice.

---

## 1. What the model previously got right

- **Criminal cases** proceed against an accused, with police investigating and gathering evidence and
  a victim in the picture.
- **Civil disputes** are between two private parties, each with their own lawyer; no police involvement.
- **Multi-judge benches exist** and are not rare edge cases.

---

## 2. What needed correcting

### 2.1 Criminal cases: the State prosecutes, not the victim
Sri Lanka follows the common-law model:
- The **state prosecutes**, not the victim. Police investigate and file the case.
- For serious (indictable) offences, the **Attorney General's Department** takes over prosecution in
  the High Court — the police do not prosecute these themselves.
- Police prosecute directly only for **minor offences in the Magistrate's Court**.
- The **victim is typically a witness**, not a party with their own lawyer arguing the case. They may
  have private counsel assist in limited ways, but they are not a third full "party".

**Consequence for the simulation:** the case structure should be **State/AG (prosecutor) vs Accused**,
with the victim folded into the **witness** role — not a third "party".

### 2.2 Bench sizes vary by court and case severity
- **High Court (normal criminal trial):** single judge in the majority of cases.
- **High Court Trial-at-Bar** (serious/high-profile cases, and the Permanent High Court at Bar for
  large financial / bribery / corruption cases): a bench of **three judges**.
- **Court of Appeal:** appeals from the High Court by **at least three judges**; appeals from a
  magistrate's court require fewer.
- **Supreme Court:** odd-numbered panels — **3, 5, or occasionally 7** — for constitutional and
  final-appeal matters.
- **District Court (civil):** single judge, always.

"3, 5, 7" is **not** random — it correlates with case severity and court level.

---

## 3. Scenario coverage

| Scenario | Parties | Prosecuting / filing side | Bench size |
|----------|---------|---------------------------|------------|
| Minor criminal (Magistrate's Court) | Police vs Accused | Police prosecutor | 1 |
| Serious criminal (High Court, ordinary) | AG vs Accused; victim as witness | AG's Department | 1 |
| High-profile / financial crime (Trial-at-Bar) | AG vs Accused(s); victim as witness | AG's Department | 3 |
| Civil dispute (District Court) | Plaintiff + counsel vs Defendant + counsel | N/A — private suit | 1 |
| Criminal appeal (Court of Appeal) | Appellant vs Respondent (AG or accused) | N/A — appeal briefs | ≥3 |
| Constitutional / final appeal (Supreme Court) | Petitioner vs Respondent | N/A | 3 / 5 / 7 |

---

## 4. What this means for the LangGraph architecture

Two structural additions (see `app/models/schemas.py` and `app/graph/trial.py`):

### 4.1 `case_type`
`case_type: Literal["criminal", "civil", "appeal"]` decides:
- whether the state (Prosecution Agent) or a private party (Plaintiff's Counsel / Appellant's Counsel
  Agent) opens the case,
- whether there is a "victim" role at all, or just a "witness" role.

### 4.2 `bench: list[JudgeProfile]` instead of a single judge
For Trial-at-Bar / Court of Appeal / Supreme Court scenarios the simulation runs **N parallel Judge
Agent calls** (each seeing the same transcript + RAG context, differing only by `JudgeProfile`) and
then a **deliberation / voting node** that aggregates their individual reasoning into a **majority
verdict**, flagging **dissent** if a judge disagrees.

This is a genuinely interesting feature for the paper: it lets the study examine how **multi-judge
deliberation differs from single-judge output** — an empirical angle that falls out naturally from
getting the architecture right.

---

## 5. Mapping to the implementation

| Concept | Code |
|---------|------|
| `case_type` | `schemas.CaseInput.case_type` (criminal / civil / appeal) |
| judge profile | `schemas.JudgeProfile` (id, pseudonym, role, bench_index) |
| bench | `schemas.CaseInput.bench: list[JudgeProfile]` |
| verdict + dissent | `schemas.Judgment` gains per-judge fields + `BenchVerdict` |
| state prosecutor vs private counsel | parameterized agents: `ProsecutionAgent` / `PlaintiffCounselAgent` / `AppellantCounselAgent` |
| victim → witness | `Party.role` = `accused | plaintiff | defendant | witness` (no standalone "victim party") |
| multi-judge graph | `judge` node becomes N parallel judge calls + a `deliberate`/vote node |

See `architecture.md` for how these plug into the LangGraph state machine, and the seed cases in
`app/seed/` which now cover each row of the scenario table.
