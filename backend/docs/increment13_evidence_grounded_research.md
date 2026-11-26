# JurisMind Increment 13 — Evidence-Grounded Research & Agent Readiness

## Purpose

Increment 12 added mock-first specialist agents and an explicitly enabled OpenAI execution path. Increment 13 addresses the next practical gap exposed during workflow testing: specialist runs can execute even when a research snapshot contains no retrieved passages.

This increment improves retrieval recall, makes repository readiness visible, and carries evidence-readiness state into the saved research and supervisor summaries.

## Changes

### 1. Controlled lexical fallback

`app/search/hybrid.py` retains strict PostgreSQL `plainto_tsquery` matching and adds a bounded OR `to_tsquery` fallback built from at most 12 normalized alphanumeric terms. Strict matches receive a stronger ranking contribution. Fallback matches are lower-weighted and remain discovery leads, not legal conclusions.

The query is passed as a bound SQL parameter. User text is not interpolated into SQL. Existing document, jurisdiction, court, year, chunk, date and authority-review filters remain in place.

### 2. Corpus-readiness endpoint

Authenticated endpoint:

`GET /research/corpus-readiness`

Returns counts for:
- all ingestion jobs;
- searchable ingestion jobs (`extracted`, `needs_ocr`);
- all staged chunks;
- searchable staged chunks;
- documents that have passed metadata review and authority verification.

It also returns `search_ready`, `authority_filtered_search_ready`, a next action, and a limitation notice.

These are availability counts only. They do not certify legal authority, currentness or proposition-to-source support.

### 3. Research snapshot status

Snapshot `summary_json` now includes:
- `evidence_ready`;
- `evidence_state` (`retrieved` or `no_search_matches`);
- an actionable `next_action`.

No new database migration is required.

### 4. Supervisor evidence status

The supervisor summary now includes:
- `evidence_count`;
- `evidence_ready`;
- `evidence_state`.

Agents continue to receive only frozen snapshot evidence IDs. Empty evidence remains an explicit `no_evidence` outcome; no sources are fabricated.

### 5. OpenAI provider test compatibility

The OpenAI client now uses the standard API base URL if a test or custom settings object does not expose `openai_base_url`. The configured application setting continues to take precedence.

## Installation

1. Extract the ZIP.
2. Copy your existing local `.env` into the extracted project root. Do not share it or commit it.
3. Activate the existing Python 3.12 virtual environment.
4. Install/update dependencies:

   `python -m pip install -r requirements.txt`

5. Start the API:

   `uvicorn app.main:app --reload`

No Alembic migration is required for Increment 13.

## Test and use

1. Run automated tests:

   `python -m pytest -q tests`

2. Open `http://127.0.0.1:8000/docs`.
3. Authenticate as a provisioned JurisMind user.
4. Call `GET /research/corpus-readiness`.
5. If `search_ready` is false, ingest PDF/HTML legal material and ensure extraction/chunk staging completes.
6. Create a new research snapshot using `POST /research/snapshots`.
7. Inspect the snapshot summary. It should say whether evidence was retrieved and suggest the next action if not.
8. Execute the specialist agents against that new snapshot. Check `evidence_count` and `evidence_ready` in the saved run summary.

## Important limitations

- The fallback is lexical, not semantic/vector retrieval.
- OR fallback can increase recall while also returning less-specific passages. Review the snippets and source metadata.
- Search results remain research leads. Citation verification and authority-status checks remain separate.
- The endpoint's counts do not prove that the corpus contains the right materials for a particular legal question.
- No live Neon, Supabase, OpenAI or external legal-source integration test is performed by this increment's automated test suite.
- The known `GET /research/agent-runs/{run_id}` 404 is deliberately not addressed here. It is parked to avoid blocking core research/agent development.

## Acceptance criteria

- Strict and fallback search query parameters are generated safely.
- Corpus-readiness counts are accurate against an empty and populated test database.
- Empty research snapshots explicitly expose `no_search_matches`.
- Supervisor summaries expose evidence readiness and do not imply evidence exists when it does not.
- Existing specialist, citation, ingestion and API unit tests continue to pass.
