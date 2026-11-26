"""PostgreSQL full-text search over staged ingestion chunks.

Results are discovery aids, not verified authorities. Pinpoints are returned only
when page-aware extraction supplied a page number. Court/jurisdiction filters are
intentionally omitted until those metadata fields are curated and persisted.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session


SEARCH_SQL = text("""
SELECT
    c.id AS chunk_id,
    c.job_id,
    j.filename,
    j.content_sha256,
    j.content_type,
    j.status,
    j.classification_json,
    c.ordinal,
    c.chunk_type,
    c.locator,
    c.heading,
    c.body_text,
    c.page_start,
    c.page_end,
    ts_rank_cd(
        to_tsvector('simple', coalesce(c.heading, '') || ' ' || c.body_text),
        plainto_tsquery('simple', :query)
    ) AS rank
FROM ingestion_chunks AS c
JOIN ingestion_jobs AS j ON j.id = c.job_id
WHERE j.status IN ('extracted', 'needs_ocr')
  AND to_tsvector('simple', coalesce(c.heading, '') || ' ' || c.body_text)
      @@ plainto_tsquery('simple', :query)
  AND (:document_type IS NULL OR j.classification_json::jsonb ->> 'document_type' = :document_type)
  AND (:created_after IS NULL OR j.created_at >= :created_after)
  AND (:created_before IS NULL OR j.created_at < :created_before)
ORDER BY rank DESC, j.created_at DESC, c.ordinal ASC
LIMIT :limit
""")


def search_legal_chunks(
    db: Session,
    query: str,
    *,
    document_type: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search staged corpus text using PostgreSQL's simple-config FTS parser."""
    clean_query = (query or '').strip()
    if not clean_query:
        raise ValueError('Search query must not be empty.')
    if not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100.')
    if created_after and created_before and created_after >= created_before:
        raise ValueError('created_after must be earlier than created_before.')
    result = db.execute(SEARCH_SQL, {
        'query': clean_query,
        'document_type': document_type,
        'created_after': created_after,
        'created_before': created_before,
        'limit': limit,
    })
    return [dict(row._mapping) for row in result]
