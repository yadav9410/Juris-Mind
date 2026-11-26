# JurisMind — Phase 1 Increment 4

PostgreSQL security validation and tenant-management foundations.

## Quick start

1. Use Python 3.11+.
2. Create/activate a virtual environment.
3. Install packages: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and configure `DATABASE_URL`.
5. Apply migrations: `alembic upgrade head`.
6. Start API: `uvicorn app.main:app --reload`.
7. Run unit tests: `pytest -q`.

Read `docs/phase1_increment4.md` before connecting Neon or running PostgreSQL integration tests. Use a disposable PostgreSQL database for tests. Do not upload confidential client files until RLS and object-storage isolation are verified.

## PostgreSQL integration tests

Set `TEST_DATABASE_URL` to a disposable PostgreSQL database and run:
`pytest -q tests/integration`

The integration tests are skipped without that variable. SQLite passing tests do not prove PostgreSQL RLS works.

## Important

This increment adds a role constraint and audit-event RLS. It does not yet provide full workspace creation, invitations, or role-checked membership-management API endpoints. See `docs/tenant_management_workflow.md` for the implementation contract.

## Ingestion pipeline — Increment 2

See `docs/ingestion_pipeline_increment2.md`. OCR uses the system Tesseract executable; install language packs for the configured OCR languages. Apply the new migration with the migration/admin connection: `alembic upgrade head`.

## Ingestion pipeline — Increment 3

Legal-aware structuring and chunking are documented in `docs/ingestion_pipeline_increment3.md`. Apply migration `0006_ingestion_chunks` using the migration/admin connection. The parser is deliberately conservative; its labels are candidates and require source review.


## Increment 4 — Page-aware extraction and legal full-text search

See `docs/ingestion_pipeline_increment4.md`. PDF chunks now retain one-based page references. PostgreSQL full-text search is exposed at `GET /search/full-text`; apply migration `0007_full_text_search` before using the endpoint. Search results are discovery aids, not verified authorities.


## Security Increment 5
See `docs/security_increment5.md`. Configure `APP_DATABASE_URL` with the `jurismind_app` role before starting the API. Keep `DATABASE_URL` for Alembic/migrations only.


## Hybrid Legal Search — Increment 4

The authenticated `GET /search/hybrid` endpoint combines PostgreSQL full-text ranking with exact phrase, heading and locator signals. It supports document-type, chunk-type, locator and ingestion-date filters. This prototype uses no paid embedding API and does not yet perform vector semantic search. See `docs/hybrid_legal_search_increment4.md` for setup, limitations and API examples.


## Search API & Retrieval Validation (Increment 5)

See `docs/search_api_retrieval_validation_increment5.md` for the test-branch migration, runtime role configuration, and read-only database validation steps. The search endpoint currently searches staged shared/public corpus records only; it is not private-tenant document search or vector semantic search.


## Increment 6 — Legal document ingestion to search integration

See `docs/increment6_ingestion_search_integration.md`. Use `python scripts/ingest_document.py <local-pdf-or-html>` with `INGESTION_DATABASE_URL` configured for `jurismind_ingest`. The authenticated API exposes read-only job status at `GET /ingestion/jobs/{job_id}`; search remains at `GET /search/hybrid`. Staged records are not published or verified authorities.

## Increment 7 — Legal source & authority metadata

Increment 7 adds candidate authority metadata and source provenance to staged ingestion jobs. Automatically extracted metadata remains explicitly unverified and pending human review. Hybrid search now supports optional jurisdiction, court and decision-year filters. See `docs/ingestion_increment7_authority_metadata.md` for migration and usage instructions.


## Increment 8 — Human metadata review & authority verification

See `docs/increment8_human_metadata_review.md` for workflow, migration, API examples and safety boundaries. Apply migration `0011_human_metadata_review` with the migration/admin database connection before using the new review endpoints.

## Increment 9 — Legal Citation & Authority Verification

Increment 9 adds the first deterministic citation verification workflow. See
`docs/increment9_citation_verification.md` for implementation scope, API usage,
migration instructions, result meanings, and known limitations.

New API routes:
- `POST /citations/verify`
- `GET /citations/{citation_id}`

New migration:
- `0012_citation_verification` (after `0011_human_metadata_review`)

The verifier is repository-bound. It does not perform live court-site searches,
comprehensive subsequent-treatment research, or proposition-to-passage legal
reasoning. Missing repository evidence is returned as `unknown` or `not_found`,
not guessed.

## Increment 10 — Research Orchestration & Research Snapshots

Increment 10 adds a workspace-scoped research workflow on top of the existing
hybrid legal search. It plans sub-questions, retrieves indexed passages and
persists a timestamped snapshot with frozen evidence references.

See `docs/increment10_research_orchestration.md` for API usage, migration,
security behavior, limitations and validation instructions.

New API routes:
- `POST /research/snapshots`
- `GET /research/snapshots?tenant_id=...`
- `GET /research/snapshots/{snapshot_id}`

New migration:
- `0013_research_snapshots` (after `0012_citation_verification`)

The planner is deterministic, and retrieval is lexical/structural. This is
not yet the six-agent or LLM-supervisor implementation.


## Increment 11 — Specialist Agent Framework (Mock-First)

Increment 11 adds six registered specialist modules and a deterministic supervisor.
The framework runs in mock mode only, stores structured evidence-linked outputs,
and does not call an LLM provider or incur API costs.

See `docs/increment11_agent_framework.md` for architecture, endpoints, migration,
security boundaries and setup instructions.

New migration: `0014_research_agent_runs` (after `0013_research_snapshots`).

New API routes:
- `GET /research/agents`
- `POST /research/snapshots/{snapshot_id}/agents/execute`
- `GET /research/agent-runs/{run_id}`

Real LLM execution is intentionally deferred to a separately approved stage.


## Increment 12 — OpenAI Execution

Increment 12 adds a guarded OpenAI provider adapter to the six Increment 11 specialists.
Mock mode remains the default. To configure the provider, add `OPENAI_API_KEY`,
`OPENAI_ENABLED=true`, and the model/token/timeout settings to the local `.env` file.
Never commit `.env` or share the key. See `docs/increment12_openai_execution.md`.

No database migration is required. The existing agent-run tables persist provider
outputs and token usage. Live execution requires a working authenticated research
snapshot and an explicitly selected `execution_mode: "openai"`.


## Increment 13

See `docs/INCREMENT13_RELEASE_NOTES.md` for evidence-grounded retrieval improvements, the corpus-readiness endpoint, installation steps, test instructions and known limitations.


## Increment 14 — Claim-to-Evidence Assessment

See `docs/INCREMENT14_RELEASE_NOTES.md` for migration, installation, API usage, interpretation limits and tests. New endpoints: `POST /research/claims/assess` and `GET /research/claims/{assessment_id}`.

Indicative post-Increment-14 roadmap is included in `docs/INCREMENT14_RELEASE_NOTES.md`.


## Increment 15 — Source Provenance & Evidence Integrity

Increment 15 adds repository-bound evidence verification. `POST /research/evidence/verify` resolves a real `ingestion_chunks.id`, checks the original file SHA-256 against the ingestion record, and optionally compares page, locator, and passage text. `GET /research/evidence/{verification_id}` retrieves the persisted tenant-scoped result.

Apply migration `0016_evidence_integrity` using the migration/admin connection (`alembic upgrade head`). The API process must be able to read the same `INGESTION_STORAGE_DIR` originals directory as the ingestion worker. Read `docs/increment15_source_provenance_evidence_integrity.md` for request examples and limitations.

A `verified` result establishes repository linkage and byte-integrity against the ingestion-time hash only. It does not independently authenticate the publisher, establish legal authority/currentness, or prove proposition support.


## Increment 16 — Legal Authority Treatment & Currentness

Increment 16 adds a workspace-scoped register of judicial treatment relationships.
A treatment assertion must reference an actual ingested chunk from the treating
judgment. Supported relationship labels include followed, relied upon, applied,
approved, affirmed, distinguished, not followed, disapproved, overruled, reversed,
modified, questioned, doubted, referred, stayed, set aside, remanded and considered.

Human review decisions are stored as append-only review events. The authority
history endpoint reports recorded and confirmed treatment counts but deliberately
returns `currentness_assessment: review_required`; it is not a comprehensive
citator and does not automatically declare an authority good law or bad law.

See `docs/increment16_authority_treatment_currentness.md` and
`docs/INCREMENT16_RELEASE_NOTES.md`.


## Increment 17 — Statutory Versioning & Temporal Law

Increment 17 adds a shared statutory corpus with statutory instruments, stable
provision identities, immutable effective-date versions and evidence-linked
amendment/commencement events. Temporal intervals are half-open
`[effective_from, effective_to)`. Overlapping versions are rejected. A date
lookup returns `complete`, `partial` or `unresolved`; it never assumes that the
latest text applied historically.

Routes are documented in `docs/increment17_statutory_versioning_temporal_law.md`.
The shared corpus is readable by provisioned workspace members; writes require
an owner/admin role. See release notes for the limitations and migration.


## Increment 18 — Legal Intelligence Engine

See `docs/INCREMENT18_RELEASE_NOTES.md` for the new structured judgment-analysis API, migration `0019_judgment_intelligence`, installation steps and limitations. New routes: `POST /research/judgments/analyses`, `GET /research/judgments`, `GET /research/judgments/{analysis_id}`, and `PATCH /research/judgments/{analysis_id}/review`.
