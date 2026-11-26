# JurisMind Hybrid Legal Search — Increment 4

## Scope
This increment upgrades the existing PostgreSQL full-text discovery endpoint into a
hybrid lexical/structural ranker. It combines PostgreSQL `simple`-configuration FTS
with exact phrase, heading, and exact locator signals. It adds filters for document
classification, chunk type, locator and ingestion creation date window, plus concise
`ts_headline` snippets.

## Deliberate prototype boundary
This is not embedding/vector semantic search. No paid API or external model is called.
The response explicitly reports `semantic_vectors_enabled: false`. Semantic retrieval
can be evaluated in a later increment using a local embedding model and pgvector only
after checking Neon extension support and local compute requirements.

## API
`GET /search/hybrid?q=section%20420&document_type=act&chunk_type=provision&locator=Section%20420&limit=20`

Optional date filters: `created_after` and `created_before` as ISO-8601 timestamps.
Existing `/search/full-text` remains as a hidden-schema compatibility path.

## Data and legal reliability limits
Search runs over `ingestion_chunks` joined to `ingestion_jobs` in `extracted` or
`needs_ocr` state. These are staged ingestion records, not a curated published corpus.
`document_type` comes from low-confidence classifier JSON. Court and jurisdiction
filters are not offered because these are not yet curated/persisted as trusted fields.
A match, score, heading or locator is not proof of authority, currentness, precedential
status, or claim support. Always inspect the original source and verify pinpoints.

## Database
No new migration is required. It reuses migration `0007_full_text_search` and the
existing `ix_ingestion_chunks_fts` GIN index. Run migrations only if your local DB has
not already reached the existing head. Do not run this new package's migrations against
Neon with `jurismind_app`; use the migration/admin role only when needed.

## Test coverage
Unit tests verify query validation, parameter forwarding, filters and SQL composition.
They do not prove PostgreSQL query execution, ranking quality, API auth end-to-end,
or production performance. A PostgreSQL smoke test against the Neon test branch is
still needed after the user installs this increment.
