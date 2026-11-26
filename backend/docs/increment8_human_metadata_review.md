# Increment 8 — Human Metadata Review & Authority Verification

## What changed
- Added `reviewed_metadata_json` separately from automated `metadata_json`.
- Added explicit review states: `pending`, `approved`, `corrected`, `rejected`.
- Added an append-only `metadata_review_events` history with reviewer identity, action, prior/resulting metadata snapshots, timestamp and note.
- Added explicit authority verification fields, including reviewer, date, reference and evidence.
- Added authenticated review queue and decision endpoints.
- Only workspace `owner` and `admin` members can review the shared corpus.
- Authority verification requires an approved/corrected decision, `source_class='primary'`, a reference and an evidence note.
- Added `authoritative_only=true` to hybrid search. It returns only extracted records with approved/corrected metadata, an explicit authority verification, and a reviewed metadata snapshot.
- Existing discovery search remains available and is explicitly not an authoritative search.

## Migration
Run using the migration/admin `DATABASE_URL`, never `jurismind_app` or `jurismind_ingest`:

```powershell
python -m alembic current
python -m alembic upgrade head
python -m alembic current
```

Expected new head: `0011_human_metadata_review`.

The migration grants the API role only SELECT plus UPDATE on the review-related columns of `ingestion_jobs`, and SELECT/INSERT on the review event table. It does not grant ingestion writes to the API role.

## API
- `GET /metadata-review/queue`
- `POST /metadata-review/jobs/{job_id}/decision`
- `GET /ingestion/jobs/{job_id}` now includes reviewed metadata and authority verification details.
- `GET /search/hybrid? q=...&authoritative_only=true` (omit the space after `?` in the actual URL).

Example correction payload:

```json
{
  "action": "correct",
  "corrected_metadata": {
    "document_type": "judgment",
    "title_candidate": "Verified title entered by reviewer",
    "year_candidate": 2025,
    "court_candidate": "Allahabad High Court"
  },
  "note": "Corrected against the official source."
}
```

Example authority verification payload (only when the source class is `primary`):

```json
{
  "action": "approve",
  "authority_verified": true,
  "authority_reference": "Official court portal case record",
  "authority_evidence": "Matched title, case number and decision date against the primary source.",
  "note": "Source checked by reviewer."
}
```

Use a real official-source reference and evidence. The examples are illustrative, not proof of any actual authority.

## Important boundaries
- Approving metadata is not the same as verifying legal authority.
- `source_class='primary'` is a necessary control in this increment, not proof that a URL is genuine. Reviewers must independently inspect the source.
- Only owner/admin membership is used as the initial reviewer gate. A dedicated corpus-curator role and finer-grained authorization can be added later.
- The audit log is append-only by application design; DB administrators can still alter database records.
- No documents are automatically promoted or published to the canonical legal corpus in this increment.
- This is a development workflow, not a production security certification.
