# Increment 15 — Source Provenance & Evidence Integrity

## Purpose

Increment 15 adds repository-bound verification for passages selected from the staged ingestion corpus. A caller must identify an actual `ingestion_chunks.id`; arbitrary evidence IDs and free-standing passage text are not treated as source records.

## What is verified

The service resolves the chunk and its ingestion job, hashes the stored original file using SHA-256, compares that hash with `ingestion_jobs.content_sha256`, and optionally checks a supplied page, locator, and passage text against the canonical stored chunk.

Verification outcomes:

- `verified`: chunk/job linkage exists, original file is present and its SHA-256 matches, and every supplied page/locator/text check matches.
- `partially_verified`: the chunk is linked but original-file integrity cannot be checked (for example, the file is missing from the configured storage location).
- `unresolved`: the chunk/job cannot be resolved, the original hash mismatches, the ingestion job is not in an extractable state, or supplied locator/page/text conflicts with stored data.

Sub-check statuses are `matched`, `mismatch`, `unavailable`, `unresolved`, or `not_supplied` as applicable.

## API

### POST `/research/evidence/verify`

Requires a Supabase bearer token and workspace membership. Viewer role cannot create a verification record.

Example request:

```json
{
  "tenant_id": "YOUR_WORKSPACE_UUID",
  "chunk_id": "ACTUAL_INGESTION_CHUNK_UUID",
  "expected_page": 12,
  "expected_locator": "Paragraph 12",
  "supplied_text": "Exact passage copied from the stored chunk."
}
```

Only `tenant_id` and `chunk_id` are required. Optional fields are compared with the stored passage. Do not send an invented ID such as a display label; obtain the actual chunk UUID from the repository/search result.

### GET `/research/evidence/{verification_id}`

Retrieves a saved verification record for a member of its workspace.

## Migration

Apply with the migration/admin connection:

```powershell
alembic upgrade head
alembic current
```

Expected revision: `0016_evidence_integrity (head)`.

The migration creates `evidence_verifications`, enables and forces PostgreSQL RLS, adds a tenant-membership policy, and grants the runtime role `jurismind_app` SELECT/INSERT.

## Important boundaries

- A matching SHA-256 proves byte-for-byte consistency with the hash stored at ingestion time. It does not prove who published or signed the document.
- Source name, URL and source class are copied from ingestion metadata. They may have been supplied by an operator and are not independently authenticated.
- A stored passage and page locator do not prove legal proposition support.
- `verified` means repository linkage and integrity checks passed, not that a court issued the document or that it remains good law.
- Original-file verification reads from `INGESTION_STORAGE_DIR` (configured as `INGESTION_STORAGE_DIR` via settings field `ingestion_storage_dir`). This increment assumes the API can access the same storage volume as the ingestion worker. If originals are in a separate machine or R2, verification will be `partially_verified` until an R2 adapter is implemented.
- The current storage adapter is local filesystem based. Do not treat local filesystem paths as a production deployment architecture.
- The verification record is an immutable snapshot of the check result; re-run verification after replacing/migrating source files.

## Tests

`tests/test_evidence_provenance.py` covers successful verification, missing original, modified original, locator/text mismatch, and unknown chunk. Run the complete suite with `pytest -q`.


### API response lifecycle note

The create-verification endpoint flushes and serializes the new record before
committing. This is intentional because tenant identity is supplied through
transaction-local PostgreSQL RLS context. Serializing an expired ORM object
after commit could initiate a new SELECT without that context.
