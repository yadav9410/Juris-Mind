# Ingestion Pipeline — Increment 1

## Included
- PDF and HTML file validation (25 MiB cap), SHA-256 fingerprinting and basic PDF signature validation.
- Original file preservation and text extraction to a local staging directory.
- HTML cleanup and PDF text extraction with page count.
- Image-only/scanned PDFs are marked `needs_ocr`; they are not silently published.
- `ingestion_jobs` tracks received/extracted/needs_ocr/failed states.
- Duplicate detection for content already extracted or awaiting OCR.
- Corpus writes use `INGESTION_DATABASE_URL`, intended for the dedicated `jurismind_ingest` database role.

## Run
1. Install `requirements.txt`.
2. Set `INGESTION_DATABASE_URL` to the dedicated ingest role connection.
3. Apply migrations using the migration/admin connection: `alembic upgrade head`.
4. Run: `python scripts/ingest_file.py path/to/document.pdf --type application/pdf`
5. HTML: `python scripts/ingest_file.py path/to/document.html --type text/html`

## Scope / limitations
This increment is a staging pipeline, not yet a published legal-corpus workflow. It does not infer legal metadata, create legal works/documents/versions, OCR scans, chunk, embed, index, or call source portals. Those are subsequent increments. Local filesystem storage is for development only; switch to private R2 before deployment. The CLI must run in a trusted ingestion environment. Do not expose it as an unauthenticated public endpoint.
