# JurisMind Increment 10 — Research Orchestration & Research Snapshots

## Purpose

Increment 10 adds the first persisted research workflow on top of the existing staged legal corpus and PostgreSQL hybrid lexical search. It accepts a legal research question, creates a transparent research plan, retrieves passages for each sub-question, and saves a timestamped snapshot with frozen evidence references.

This is a workflow foundation. It is not yet the six-agent system, an LLM supervisor, or a legal-opinion generator.

## Included

- Workspace-scoped research snapshot model.
- Frozen evidence-reference model recording retrieval query, source chunk/job identifiers, filename, locator, page range, retrieved fields and capture timestamp.
- Conservative deterministic research planner:
  - Uses supplied sub-questions when the caller provides them.
  - Otherwise splits only clear clauses/explicit separators and preserves the original question.
  - Caps plans at eight sub-questions.
- Retrieval through the existing `search_legal_chunks_hybrid` service.
- Workspace role check: `owner`, `admin` and `member` can create; `viewer` is read-only.
- Authenticated API:
  - `POST /research/snapshots`
  - `GET /research/snapshots?tenant_id=...`
  - `GET /research/snapshots/{snapshot_id}`
- Alembic migration `0013_research_snapshots`, following `0012_citation_verification`.
- PostgreSQL forced RLS policies for both new tables and SELECT/INSERT grants for `jurismind_app`.

## API example

`POST /research/snapshots`

```json
{
  "tenant_id": "YOUR_WORKSPACE_TENANT_ID",
  "question": "What is the legal test for bail and how have courts applied it?",
  "jurisdiction": "India",
  "court": "Supreme Court of India",
  "sub_questions": [
    "What statutory provisions govern the bail test?",
    "How has the Supreme Court applied the bail test?"
  ],
  "per_query_limit": 10
}
```

The API returns the snapshot ID, original question, plan, query/result counts, status, timestamp and limitations notice. Retrieved passages are available through the snapshot GET route.

## Snapshot semantics

A snapshot preserves the result fields returned at retrieval time as JSON evidence records. It also stores chunk/job IDs as references to repository records. The referenced repository documents remain the source of truth; the snapshot does not copy or replace original documents.

## Security

- Every request requires the existing Supabase/JurisMind authentication dependency.
- Create requires membership in the explicitly selected tenant.
- Viewer role cannot create snapshots.
- Snapshot reads are scoped through membership checks.
- PostgreSQL RLS is enabled and forced on both new tables.
- Runtime role receives SELECT and INSERT only from this migration; no UPDATE/DELETE grant is added.

This does not certify end-to-end tenant isolation. Validate PostgreSQL policies and runtime grants on the target Neon branch before production use.

## Explicit limitations

1. Planning is deterministic and rule-based, not AI-generated legal analysis.
2. Retrieval uses the existing PostgreSQL full-text/phrase/heading/locator search. Semantic vectors are not enabled.
3. A retrieval hit is a research lead, not proof of relevance, correctness, authority or legal proposition support.
4. The snapshot does not yet invoke specialist agents, an LLM supervisor, citation verification automatically, or memo drafting.
5. Results depend on the quality, completeness and currentness of the indexed corpus.
6. This increment does not resolve the deferred Increment 8 authenticated account lookup issue. Authenticated API testing may remain blocked until that issue is addressed.

## Setup and validation

From the project root in PowerShell:

```powershell
# Activate the existing Python 3.12 virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies if needed
python -m pip install -r requirements.txt

# Apply migration with DATABASE_URL using the dedicated migration/admin role
python -m alembic upgrade head

# Confirm the database revision
python -m alembic current

# Run the complete suite
python -m pytest -q

# Start the API
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and use the Legal Research Orchestration section. An authenticated request requires a provisioned JurisMind user and tenant membership.

## Next architectural step

Use the saved research snapshot as the stable input/output contract for specialist-agent orchestration. Agents should receive bounded sub-questions and retrieved evidence references, return structured findings with citations, and never directly certify authority status or mutate the legal corpus.
