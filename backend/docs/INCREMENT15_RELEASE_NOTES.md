# JurisMind Increment 15 — Release Notes

## Delivered

- Added `EvidenceVerification` persistence model.
- Added deterministic provenance/integrity service resolving actual `IngestionChunk` records.
- Added SHA-256 re-hashing of the stored original file and comparison with the ingestion-time `IngestionJob.content_sha256`.
- Added optional page, locator, and exact normalized passage-text comparisons.
- Added outcome classifications: `verified`, `partially_verified`, and `unresolved`.
- Added independent sub-check statuses for file integrity, locator and passage text.
- Added authenticated workspace-scoped API:
  - `POST /research/evidence/verify`
  - `GET /research/evidence/{verification_id}`
- Added migration `0016_evidence_integrity` with tenant RLS and runtime SELECT/INSERT grants.
- Registered the model and API router; added API documentation and five focused service tests.

## Validation performed in build environment

- `pytest -q tests`: **77 passed, 3 skipped**.
- Python compilation check for application, migration and test modules: passed.
- No live Neon migration, Supabase-authenticated API request, R2 storage test, or production deployment test was performed.

## Migration

From the project root, with the existing `.env` configured:

```powershell
alembic upgrade head
alembic current
```

Expected head: `0016_evidence_integrity`.

## Storage requirement

The API process must be able to read the same originals directory configured by `INGESTION_STORAGE_DIR`. This increment uses the existing local-filesystem ingestion storage. For a split deployment or Cloudflare R2, a shared-volume or R2 storage adapter is still required.

## Known limitations

- Hash comparison proves that current original-file bytes match the hash recorded at ingestion. It does not independently establish publisher identity, court authenticity, signature validity, or legal status.
- Source labels/URLs/classes remain ingestion metadata and are not independently authenticated.
- Page/locator/text matching validates repository consistency, not legal support for a proposition.
- The existing shared corpus remains shared; verification records are workspace-scoped.
- Full PostgreSQL RLS behavior and tenant isolation require live integration tests against the configured Neon roles.


## Fix 2 — response serialization under transaction-local RLS

A live API smoke test exposed `sqlalchemy.orm.exc.ObjectDeletedError` after the
verification row was committed. The endpoint serialized an ORM object after
`commit()`, when SQLAlchemy had expired its attributes and the transaction-local
RLS identity context had ended. The endpoint now calls `flush()`, serializes the
response while the authenticated transaction is active, and then commits.

This is a targeted API response-lifecycle fix. It does not change the database
schema or require another Alembic migration. The existing automated suite was
rerun: 77 passed, 3 skipped. A live Neon/Supabase retest remains required.
