# Increment 7 — Legal Source & Authority Metadata

## What changed

- Staged ingestion jobs now retain a structured `metadata_json` candidate record.
- Metadata includes the existing document type, title, year, court and neutral-citation candidates, plus jurisdiction and a conservatively parsed decision-date candidate.
- Every automatically extracted metadata record is marked `verified: false` and `metadata_review_status: pending`.
- Optional source provenance can be supplied at ingestion: source name, exact source URL, and source class (`primary`, `secondary`, or `unverified`). The default is `unverified`.
- The ingestion status endpoint returns metadata candidates, review status and provenance without exposing local storage paths.
- Hybrid search accepts optional jurisdiction, court and decision-year filters.

## Migration

Apply `0010_legal_authority_metadata` after `0009_search_runtime_read_access` using the migration/admin database URL on the **jurismind-security-test** branch:

```powershell
python -m alembic current
python -m alembic upgrade head
python -m alembic current
```

Do not run migrations using `jurismind_app` or `jurismind_ingest`.

## Example ingestion

```powershell
python scripts/ingest_document.py "C:\path\to\document.pdf" --source-name "India Code" --source-url "https://www.indiacode.nic.in/" --source-class primary
```

Only label a source `primary` after you have independently checked that the specific document is from an official primary source. Public availability does not itself establish reuse permission.

## Example search

```text
GET /search/hybrid?q=natural%20justice&jurisdiction=Uttar Pradesh%2C%20India&court=Allahabad%20High%20Court&decision_year=2025
```

## Important limitations

- These are candidate metadata fields, not verified legal facts.
- Date extraction currently recognizes a limited textual form such as `12 February 2025`; other formats may remain null.
- Jurisdiction extraction is heuristic and limited to explicit India/Uttar Pradesh references.
- No endpoint currently approves metadata or publishes a staged document into the shared legal corpus. Human verification and publication controls remain a later increment.
- Search remains PostgreSQL lexical/structural retrieval; semantic embeddings are not enabled.
