# Increment 18 — Legal Intelligence Engine

This release adds evidence-linked structured judgment analysis. It builds on (and does not replace)
Increment 17 statutory versioning, Increment 16 authority-treatment records, and Increment 9 citation verification.

## Included capability

- Store structured judgment records: case title/citation, court/date/bench, facts, issues,
  party arguments, holdings, ratio, final order and cited authorities.
- Every analysis is anchored to an existing ingestion job and a chunk belonging to that job.
- Workspace membership controls reads; viewers cannot create records; only owners/admins can
  change review status.
- Records remain explicitly `pending_review` until a workspace owner/admin marks them reviewed.
- Source chunk linkage is traceability, not proof that every extracted proposition is correct.
- Existing statutory events and versions remain the amendment/commencement history source.
- Existing citation verification and authority treatment remain the citation/currentness evidence
  workflows; this increment does not claim to be a comprehensive citator or automated legal conclusion.

## Migration

Apply using the migration/admin connection:

```powershell
alembic upgrade head
```

New migration: `0019_judgment_intelligence` (after `0018_statutory_temporal`).

## API

All routes require the existing authenticated API session and workspace membership.

### Create a structured analysis

`POST /research/judgments/analyses`

```json
{
  "tenant_id": "WORKSPACE_UUID",
  "ingestion_job_id": "INGESTION_JOB_UUID",
  "source_chunk_id": "INGESTION_CHUNK_UUID",
  "case_title": "A v B",
  "citation": "(2024) 1 SCC 100",
  "court": "Supreme Court of India",
  "decision_date": "2024-01-15",
  "bench": ["Justice A", "Justice B"],
  "facts": ["Material fact 1"],
  "issues": ["Whether ...?"],
  "arguments_petitioner": ["Submission ..."],
  "arguments_respondent": ["Submission ..."],
  "holdings": ["The Court held ..."],
  "ratio_decidendi": "Human-reviewed ratio text",
  "final_order": "Appeal allowed/dismissed ...",
  "cited_authorities": ["X v Y, (2020) 1 SCC 1"],
  "limitations": ["Any uncertainty or missing passage"]
}
```

The `source_chunk_id` must belong to the supplied `ingestion_job_id`. The source job must be in
an extractable state (`extracted` or `needs_ocr`). Lists are structured text supplied by a user or
downstream review process; the API does not autonomously infer a ratio from a PDF.

### List/search records

`GET /research/judgments?tenant_id=...&citation=...&q=...&limit=50`

### Get a record

`GET /research/judgments/{analysis_id}`

### Set review status

`PATCH /research/judgments/{analysis_id}/review`

```json
{"review_status": "reviewed"}
```

Allowed values: `pending_review`, `reviewed`, `rejected`. Only workspace owners/admins can change it.

## Install on Windows PowerShell

1. Stop the running API (`Ctrl+C`).
2. Extract this ZIP into a new folder first, so you can inspect the included project.
3. Back up your current project folder and database before applying the update.
4. Copy the package's `app`, `migrations`, `tests`, and `docs` folders into the existing project,
   allowing the included changed files to merge/replace. Do not replace your `.env`.
5. From the project root, activate your existing virtual environment.
6. Run:

```powershell
alembic upgrade head
pytest -q tests/test_judgment_intelligence_contract.py
uvicorn app.main:app --reload
```

7. Open `http://127.0.0.1:8000/docs` and confirm the `judgment-intelligence` routes appear.

The migration must be applied once to the same database used by the running API. Do not run
`alembic downgrade` as a routine rollback; take a database backup first.

## Important deployment note

The PostgreSQL migration installs RLS policies and grants SELECT/INSERT to `jurismind_app`.
Review status changes are owner/admin-only at the API layer. The migration is additive and does
not modify existing Increment 17 tables.

## Validation performed for this package

- New request-contract tests: 2 passed.
- Python syntax compilation: run during packaging.
- PostgreSQL migration/RLS behavior and end-to-end authenticated requests were not exercised
  against the user's live database. Validate those in the target environment.
