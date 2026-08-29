# AI Judge — Legal Corpus Sources (Sri Lanka, English)

This catalog lists the English-language sources for building the RAG corpus. It is a
**working list** — some are downloaded, others are pending crawl. All statutes are official
government texts (public domain as state legislation); judgment collections may have
additional terms. Verify licensing before bulk redistribution.

Legend: ✅ downloaded to `corpus/raw/` · ⏳ pending crawl · ❌ blocked/unreachable

---

## Primary statutes (official, English)

| Act | Source | URL | Status |
|-----|--------|-----|--------|
| Code of Criminal Procedure Act | lankalaw.net | `https://lankalaw.net/wp-content/uploads/2025/02/1956Y1V20C.html` | ✅ `cpc_act.txt` (362k chars) |
| Penal Code (Consolidated) 2024 | lankalaw.net | `https://lankalaw.net/wp-content/uploads/2025/03/Penal-Code-Consolidated2024.pdf` | ✅ `penal_code.txt` (362k chars) |
| Evidence Ordinance (Consolidated) 2024 | lankalaw.net | `https://lankalaw.net/wp-content/uploads/2025/03/Evidence-Ordinance-Consolidated-2024.pdf` | ✅ `evidence_ordinance.txt` (153k chars) |
| Constitution of the DSR of Sri Lanka | Supreme Court / govt mirrors | `https://supremecourt.lk/wp-content/uploads/2025/...` (search) | ⏳ verify |
| Bail Act No. 30 of 1997 | (search pending) | — | ⏳ |
| Judicature Act No. 2 of 1978 | lankalaw.net | `https://lankalaw.net/judicature-acts/` | ⏳ |
| Constitution (alt mirrors) | irrigation.gov.lk, languagesdept.gov.lk, balangoda.uc.gov.lk | (search) | ⏳ |

## Court / judgment sources (English)

| Collection | Source | URL | Status |
|------------|--------|-----|--------|
| Sri Lanka Law Reports / judgments | CommonLII – Sri Lanka | `http://www.commonlii.org/lk/` | ❌ 403 bot-blocked (try later) |
| Judgment e-library | Judicial Service Commission | `https://www.judiciary.gov.lk/` | ⏳ |
| Lawnet | lawnet.gov.lk | `https://www.lawnet.gov.lk/` | ❌ TLS blocked |

## Additional legal portals (to explore / crawl later)

| Platform | URL | Notes |
|----------|-----|-------|
| Lanka Law | `https://lankalaw.net` | AI legal Q&A; hosts consolidated act PDFs (source of current downloads) |
| Justice.lk | `https://justice.lk` | 26 free legal guides; court hierarchy; major statutes |
| Iuris Scientia AI — Legal Library | `https://iuris.lk/legal-library` | Sri Lanka legal corpus, judgment & Act previews, AI summaries |
| Lexelon | `https://lexelon.net` | Articles, legal guides, stamp-duty tools |
| The Legal Database | `https://thelegaldatabase.com` | Up-to-date laws, cases, regulations |
| LawConnect | `https://lawconnect.lk` | AI legal knowledge + verified lawyer connect |
| Guide to Law Online: Sri Lanka | `https://guides.loc.gov/law-sri-lanka` | Law Library of Congress link hub (constitution, branches, free sources) |

---

## How to add / re-crawl

1. Put source URLs + license in this table.
2. `python corpus/collect.py --only <name>` fetches and extracts to `corpus/raw/<name>.txt`.
3. Ingest with `python backend/ingest_corpus.py` (structure-aware chunking: `s.N:`/`N.` for
   statutes, `Facts/Issues/Reasoning/Held` for judgments, `Article N:` for the constitution).
