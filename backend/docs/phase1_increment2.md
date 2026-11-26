# Phase 1 — Increment 2: Database Design and Migrations

## Scope delivered

This increment establishes the first relational shape of the shared legal repository, preserves the Increment 1 workspace/user tables, and introduces Alembic for controlled schema evolution.

## Main relationships

- One `legal_work` can have multiple `legal_documents` (for example, the same judgment on an official portal and a permitted secondary source).
- Each `legal_document` belongs to one `source_record` and can have multiple immutable `document_versions`.
- Each version can contain many `legal_provisions` or `judgment_paragraphs`.
- `document_events` attach legal-history events to a legal work and can point to the evidence version.
- `audit_events` can record actions associated with a tenant and actor.

## Deliberate limitations

- No tenant-owned file/document table yet; public corpus is shared and private user uploads are a separate upcoming design.
- No PostgreSQL RLS policies yet.
- No pgvector columns yet; extension and embedding model choices belong to the search/indexing increment.
- No automatic inference of commencement/effective dates.
- No legal relationship graph or proposition-level case treatment yet.
- Audit-event immutability is an application policy at this stage, not a database-enforced guarantee.

## Acceptance checks

- All expected tables register in SQLAlchemy metadata.
- Two different captured hashes can be stored as separate versions of one legal document.
- Alembic can create the schema on an empty local database and report the current revision.
- Existing API and contract tests continue to pass.
