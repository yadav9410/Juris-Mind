# JurisMind Increment 5 — Search API & Retrieval Validation

## Scope

This increment validates the authenticated hybrid lexical-search API against the shared **staged public corpus** (`ingestion_jobs` + `ingestion_chunks`). It does not add vector embeddings, private-tenant document search, legal-authority verification, or a claim that retrieved text is legally current.

## Changes

- Keep `GET /search/hybrid` as the primary authenticated search endpoint.
- Add migration `0009_search_runtime_read_access`: grants `jurismind_app` SELECT only on the shared staging search tables. The role receives no write privileges from this migration.
- Add API contract tests for authentication, response shape, discovery warning, and missing query validation.
- Add an optional read-only PostgreSQL smoke test using `TEST_DATABASE_URL`.
- Add `scripts/validate_search_database.py` to check migration/index state with the test-branch admin URL and execute a real search query through the runtime URL. It performs no data writes.

## Important boundaries

- `ingestion_chunks` currently represents staged shared/public-source ingestion. These tables are not tenant-private document storage. Do not upload confidential client documents into this corpus.
- The endpoint requires a valid Supabase JWT and a provisioned `app_users` mapping. API tests override authentication only to test the response contract; they do not validate live Supabase JWKS verification.
- Ranking is lexical/structural (PostgreSQL FTS, phrase, heading, locator). `semantic_vectors_enabled` remains false.
- A result is a discovery lead, not a verified authority or a legal opinion. Verify original source, version, jurisdiction, legal status, and pinpoint.
- Page locators may be null until page-aware extraction is available.

## Test-branch setup

1. In Neon, select the `jurismind-security-test` branch.
2. Set `DATABASE_URL` to the branch's `neondb_owner` connection string for Alembic and read-only schema inspection only.
3. Run `alembic upgrade head`. This should apply `0009_search_runtime_read_access` after `0008_identity_tenant_isolation`.
4. Set `APP_DATABASE_URL` to the `jurismind_app` connection string for the same branch.
5. Set `TEST_DATABASE_URL` to that same restricted `jurismind_app` connection string for the optional read-only PostgreSQL smoke test.
6. Run `python scripts/validate_search_database.py` (reads `DATABASE_URL` for migration/index/grant checks and `APP_DATABASE_URL` for the actual search).
7. Run `python -m pytest -q`.

Never paste connection strings or passwords into chat. Do not use the production branch for these checks.
