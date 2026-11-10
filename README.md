# UAE GovGuide AI — AI for Good Lab UAE Hackathon

**Sector:** Public Services & Digital Government  
**Release:** V5.1 — submission snapshot 10 November 2026  
**Status:** Independent research prototype; **not** an official UAE government service.  
**Public data snapshot:** Manually curated on 9 November 2026; re-check ICP sources before any real-world use.

## What it does

A bilingual, policy-aware government service navigator. It asks for non-identifying eligibility information, retrieves source-grounded public-service documentation, validates decision rules and guides users through the steps. For in-person service it filters documented ICP centres by *supported service, applicant class, emirate, locality* and centre status. The result is not a real-world distance ranking or live booking availability.

**Prototype coverage:** 3 executable ICP Emirates ID service workflows; 2 reference-only catalogue records; 13 documented centre records; curated UAE policies and standards. The system does not submit applications or log in to UAE PASS.

## Quick start — Windows PowerShell

Open PowerShell **inside this folder** and run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If `.venv` already exists, omit the first command. No activation needed. Browser URLs:
- Conversational agent: http://127.0.0.1:8000/assistant
- Verified centre locator: http://127.0.0.1:8000/locator
- Structured simulation: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs

## Test and reproduce

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe scripts/stage5_evaluate.py
```

**Evidence (local, 10 Nov 2026):** 69/69 unit/integration tests passed in this repository. The pre-existing offline benchmark is a **curated synthetic** 36/36 case suite across intent, retrieval, decisions, locator and sources. These are not estimates of general accuracy, correctness for all services, or live centre availability. The cloud LLM variant was not independently evaluated.

## Architecture

`official source -> manual structured extraction -> data/*.json/csv -> scripts/build_kb.py -> character ngram TF-IDF retrieval -> app.dialogue -> app.core policy checks -> app.centre_guidance/app.locator -> web UI + explainable audit`

- `app/main.py` — FastAPI routing
- `app/dialogue.py` — multi-turn state, clarification and extraction
- `app/core.py` — source-linked deterministic eligibility, workflow and alerts
- `app/locator.py` / `app/centre_guidance.py` — documented centre matching and explanation
- `app/cloud.py` — optional opt-in external LLM, disabled by default
- `data/sources.json` — publisher, provenance, review date, URLs
- `data/policies.json` — policies, strategies and standard mappings
- `data/kb.jsonl` — retrieval corpus
- `data/policy_conflicts.json` — conflicts requiring human review

The research *hypotheses* in `docs/policy_gap_hypotheses.json` are not claims that laws were violated or existing regulators are non-compliant.

## Security, ethical boundaries and limits

- Never ask for Emirates ID number, passport number, UAE PASS credentials or identity images.
- API keys belong in a local `.env` file (never committed). `.gitignore` excludes `.env` and `.venv`.
- External LLM is opt-in. Never present a locally working deterministic prototype as a cloud GPT deployment.
- No official portal connection, transaction submission, live queue/open-now data, verified geocoordinates, travel-time optimisation or official legal advice.
- Centre eligibility must always be confirmed with ICP; the dataset is a snapshot.
- Y.3172 mapping is conceptual, not a claim of formal conformance or certification.

## Submission attachments

- `docs/Technical_Report_5_pages.pdf` — report draft for transfer to the **official ITU template**.
- `docs/Technical_Report_EDITABLE.md` — report source for editing.
- `docs/SUBMISSION_GUIDE_AR.md` — Arabic upload, GitHub and final checklist.
- `docs/DEMO_SCRIPT_AR.md` — 4–6 minute live-video walkthrough.
- `docs/POLICY_AND_GAPS.md` — explicit governance and standards traceability.
- `artifacts/stage5_evaluation.json` and `artifacts/Stage5_Evaluation.xlsx` — synthetic testing results.

**Official challenge page:** https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/ 
