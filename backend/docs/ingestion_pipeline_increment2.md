# JurisMind Ingestion Pipeline — Increment 2

## Included
- OCR fallback for low-text PDF pages using PyMuPDF's Tesseract integration.
- OCR language selection through `OCR_LANGUAGES` (default `eng`).
- Per-page OCR fallback; pages with sufficient native text are not OCRed.
- Rule-based legal document classification hints: judgment, Act, rules, notification, order, unknown.
- Candidate title, year, court and neutral citation extraction.
- Human-review flag on every classification; candidates are not treated as verified legal metadata.
- Migration `0005_ocr_classification` adds `ocr_used` and `classification_json` to `ingestion_jobs`.

## System requirement
Install Tesseract OCR on the host. For Hindi OCR, install the Hindi language data and set:
`OCR_LANGUAGES=eng+hin`
OCR remains best-effort. If Tesseract or a requested language is unavailable, the job is retained as `needs_ocr` where extracted text remains below the configured threshold.

## Configuration
```env
OCR_ENABLED=true
OCR_LANGUAGES=eng
OCR_MIN_TEXT_CHARS=80
```

## Apply
Use the migration/admin connection:
`alembic upgrade head`

## Important limits
Classification is deterministic metadata suggestion, not a legal conclusion. Court, year, title and citation candidates require source verification. OCR text can contain recognition errors; preserve the original PDF and do not publish extracted OCR text as verified authority without validation.
