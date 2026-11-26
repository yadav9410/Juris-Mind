# Increment 4 — Page-aware extraction and PostgreSQL full-text search

## What changed

1. PDF extraction now retains each page's extracted/OCR text with a one-based page number. The existing combined extracted text is still preserved.
2. PDF staging chunks are structured page-by-page and store `page_start` and `page_end`. HTML has no intrinsic pagination, so its page fields remain null.
3. Added PostgreSQL full-text search over staged `ingestion_chunks`, ranked with `ts_rank_cd` and accelerated by a GIN expression index.
4. Added `GET /search/full-text?q=...&document_type=...&limit=...` for discovery of staged passages.
5. Search responses include source job, filename, SHA-256, chunk locator, and page pinpoint fields.

## Migration

`0007_full_text_search` follows `0006_ingestion_chunks`. On PostgreSQL it creates the GIN index. On SQLite it is a no-op so local tests can continue; the search endpoint itself requires PostgreSQL full-text search.

Run with the migration/admin `DATABASE_URL`:

```powershell
alembic upgrade head
```

## Search usage

```http
GET /search/full-text?q=natural justice&document_type=judgment&limit=10
```

The endpoint searches only staged ingestion material with status `extracted` or `needs_ocr`. It does not publish documents into the shared corpus and does not treat results as verified legal authority.

## Scope and limitations

- PDF page references are one-based source pages and are only as reliable as the PDF extraction/OCR text. They are not printed page labels or paragraph-level pinpoint verification.
- Page-by-page chunking deliberately avoids guessing cross-page boundaries. A legal provision spanning pages may appear in separate page chunks.
- HTML page references remain null.
- Classification is heuristic and marked for human review. The initial filter is limited to `document_type`; court, jurisdiction, date-of-law and authority-status filters are not offered because those fields are not yet curated and persisted in this staging schema.
- This increment implements lexical full-text retrieval, not vector/semantic retrieval. pgvector and a local embedding model are a later, separately tested stage; no paid embedding API is called.
- Search is a discovery aid. Verify the original source, legal status, temporal applicability and pinpoint before relying on any result.
- Local development storage remains filesystem-based. Move originals and derived files to private object storage before deployment.
