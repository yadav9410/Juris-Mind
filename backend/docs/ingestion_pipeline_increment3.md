# Ingestion Pipeline — Increment 3: Legal-aware structuring and chunking

## What this increment adds
- Conservative detection of section/article/rule headings in legislation and numbered paragraphs in judgments.
- Schedule heading detection.
- Legal-aware chunks with ordinal, type, locator and source text.
- Bounded chunk splitting for oversized passages, with a small overlap.
- Staging table `ingestion_chunks`, linked to an ingestion job ID.
- Chunks are **not** yet published into the shared legal corpus or marked as verified authority.

## Apply the migration
Use the migration/admin connection and run:

```bash
alembic upgrade head
```

This applies `0006_ingestion_chunks` after `0005_ocr_classification`.

## How to interpret output
`section`, `article`, and `rule` labels are detected from textual headings. Judgment paragraph numbers are detected from simple numbered-line patterns. Complex formatting, tables, footnotes, multi-column PDFs, Hindi text, and OCR errors may prevent accurate detection. Always compare extracted structure with the original document.

All chunks preserve the source job ID and original file/text references stored by the ingestion job. Page pinpoint mapping is not inferred in this increment and remains null until page-aware extraction is added.

## Next increment
Add page-aware parsing and validation, then embeddings and hybrid search. Do not index or expose unreviewed staging chunks as verified legal authority.
