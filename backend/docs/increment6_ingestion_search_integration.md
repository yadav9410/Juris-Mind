# JurisMind Increment 6 — Legal Document Ingestion to Search Integration

## What this increment adds

- A simple local CLI to submit one PDF or HTML file to the existing deterministic ingestion pipeline.
- A read-only authenticated API endpoint to inspect an ingestion job and its staged chunk count.
- A documented workflow connecting ingestion, PostgreSQL full-text indexing, and the existing hybrid search endpoint.
- No new migration: this increment uses the existing `ingestion_jobs`, `ingestion_chunks`, and GIN index from migrations 0004–0009.

## Security boundary

- `INGESTION_DATABASE_URL` must use the restricted `jurismind_ingest` role. The CLI uses this connection for writes.
- `APP_DATABASE_URL` must use the restricted `jurismind_app` role. The API uses it for reads and search.
- `DATABASE_URL` remains reserved for Alembic/migrations and must not be used for routine ingestion or API traffic.
- Do not expose the ingestion CLI as an unauthenticated public upload endpoint.
- The new `GET /ingestion/jobs/{job_id}` endpoint is authenticated and read-only. It does not return local storage paths.
- Ingested files are staged. They are not automatically published, verified, or represented as authoritative legal sources.

## Local setup

1. Activate the project's Python virtual environment.
2. Install dependencies if needed: `python -m pip install -r requirements.txt`.
3. Confirm `.env` has `INGESTION_DATABASE_URL` set to the `jurismind_ingest` connection and `APP_DATABASE_URL` set to `jurismind_app`.
4. Keep `DATABASE_URL` for migration/admin work only.
5. Confirm `INGESTION_STORAGE_DIR` points to a writable local development folder. Local filesystem storage is for development only; deployment needs private object storage such as R2.

## Ingest one file

From the project root:

```powershell
python scripts/ingest_document.py "C:\path\to\sample-act.pdf"
```

Or:

```powershell
python scripts/ingest_document.py "C:\path\to\judgment.html"
```

The command prints a JSON summary including the job ID, status, content hash, classification hints, and chunk count. Save the `job_id`.

Supported inputs are PDF and HTML/HTM, subject to the existing 25 MiB validation limit. OCR requires the Tesseract executable and configured language data. OCR/classification/structure output is best-effort and requires human source review.

## Verify the job

With a valid Supabase bearer token for a provisioned JurisMind user:

```http
GET /ingestion/jobs/{job_id}
Authorization: Bearer <access-token>
```

The response includes status and staged chunk count. It deliberately does not expose filesystem paths.

## Search the ingested document

After ingestion reports `status` as `extracted` or `needs_ocr` and `chunk_count` greater than zero, use:

```http
GET /search/hybrid?q=Section%203&limit=10
Authorization: Bearer <access-token>
```

Use a phrase known to exist in the uploaded source. Search results include the filename, SHA-256, chunk locator, and available one-based PDF page references. HTML page references remain null.

## Duplicate handling

A repeated upload with the same SHA-256 and an already extracted/needs_ocr job returns the existing job as `duplicate` rather than creating another copy of its staged chunks.

## Known limitations

- This increment does not publish staged records into `legal_works` / `legal_documents` / `document_versions`.
- No semantic/vector search is enabled; the search ranker remains PostgreSQL lexical full-text plus phrase/heading/locator signals.
- Local filesystem storage is not suitable for hosted deployment or multiple workers. Move originals and extracted text to private object storage before deployment.
- Page/section detection is heuristic. Pinpoints must be checked against the original document.
- Search is shared staged-corpus search, not tenant-private document search.
- Source licensing/terms and provenance must be reviewed before bulk acquisition or publication.

## Tests

Run:

```powershell
python -m compileall -q app scripts
python -m pytest -q
```

PostgreSQL-specific GIN/RLS behavior must still be validated against the test branch; SQLite unit tests do not establish those properties.
