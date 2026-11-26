# Increment 16 Release Notes

## Added
- Evidence-linked judicial authority treatment records.
- Supported treatment labels covering positive, adverse, procedural and neutral treatment.
- Validation that the evidence chunk belongs to the supplied treating ingestion job.
- Optional link to an Increment 15 evidence-verification record from the same tenant and chunk.
- Append-only human review events, restricted to workspace owners/admins.
- Treatment retrieval and citation-specific workspace history endpoint.
- Conservative currentness output that remains `review_required`.
- Tenant RLS policies and runtime SELECT/INSERT grants.

## Migration
- Revision: `0017_authority_treatment`
- Parent: `0016_evidence_integrity`
- Revision identifier length: 24 characters (within the Alembic/PostgreSQL 32-character limit).
- Creates `authority_treatments` and `authority_treatment_reviews`.

## API routes
- `POST /research/authority/treatments`
- `GET /research/authority/treatments/{treatment_id}`
- `POST /research/authority/treatments/{treatment_id}/review`
- `GET /research/authority/history`

## Validation
- Full automated test suite: 81 passed, 3 skipped.
- Python compilation of changed modules: passed.
- ZIP integrity check: passed.
- Alembic revision chain checked in source: `0016_evidence_integrity` -> `0017_authority_treatment`.

## Not performed
- No migration against the user's live Neon database.
- No live Supabase-authenticated API test.
- No live judicial authority or currentness determination.
- No external citator integration.
