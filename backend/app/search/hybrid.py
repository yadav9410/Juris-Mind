"""PostgreSQL hybrid lexical search with reviewed-metadata precedence."""
from __future__ import annotations
from datetime import datetime
import re
from sqlalchemy import text
from sqlalchemy.orm import Session

HYBRID_SEARCH_SQL = text("""
WITH job_metadata AS (
    SELECT j.*,
        CASE WHEN j.metadata_review_status IN ('approved', 'corrected')
                  AND j.reviewed_metadata_json IS NOT NULL
             THEN coalesce(j.metadata_json::jsonb, '{}'::jsonb) || j.reviewed_metadata_json::jsonb
             ELSE coalesce(j.metadata_json::jsonb, '{}'::jsonb)
        END AS effective_metadata,
        coalesce(j.classification_json::jsonb, '{}'::jsonb) AS classification
    FROM ingestion_jobs j
),
candidates AS (
    SELECT c.id AS chunk_id, c.job_id, j.filename, j.content_sha256,
        j.content_type, j.status, j.source_name, j.source_url, j.source_class,
        j.metadata_review_status, j.authority_verified, j.authority_reference,
        j.effective_metadata, j.classification,
        coalesce(j.effective_metadata ->> 'document_type',
                 j.classification ->> 'document_type') AS effective_document_type,
        c.ordinal, c.chunk_type, c.locator, c.heading, c.page_start, c.page_end,
        c.body_text,
        to_tsvector('simple', coalesce(c.heading, '') || ' ' || c.body_text) AS search_vector,
        plainto_tsquery('simple', :query) AS search_query,
        to_tsquery('simple', :fallback_query) AS fallback_query,
        lower(coalesce(c.heading, '') || ' ' || c.body_text) LIKE :exact_pattern AS exact_phrase,
        lower(coalesce(c.heading, '')) LIKE :exact_pattern AS heading_match,
        (CAST(:locator AS text) IS NOT NULL AND lower(coalesce(c.locator, '')) = lower(CAST(:locator AS text))) AS locator_match
    FROM ingestion_chunks c
    JOIN job_metadata j ON j.id = c.job_id
    WHERE j.status IN ('extracted', 'needs_ocr')
      AND (
        CAST(:authoritative_only AS boolean) IS FALSE
        OR (j.metadata_review_status IN ('approved', 'corrected')
            AND j.authority_verified IS TRUE
            AND j.reviewed_metadata_json IS NOT NULL
            AND j.source_class = 'primary')
      )
      AND (
        CAST(:document_type AS text) IS NULL
        OR coalesce(j.effective_metadata ->> 'document_type',
                    j.classification ->> 'document_type') = CAST(:document_type AS text)
      )
      AND (CAST(:jurisdiction AS text) IS NULL
           OR lower(trim(coalesce(j.effective_metadata ->> 'jurisdiction_candidate',
                                  j.classification ->> 'jurisdiction_candidate', '')))
                = lower(trim(CAST(:jurisdiction AS text)))
           OR (lower(trim(CAST(:jurisdiction AS text))) = 'india'
               AND lower(trim(coalesce(j.effective_metadata ->> 'jurisdiction_candidate',
                                       j.classification ->> 'jurisdiction_candidate', '')))
                   LIKE '%, india'))
      AND (CAST(:court AS text) IS NULL
           OR lower(coalesce(j.effective_metadata ->> 'court_candidate', '')) = lower(CAST(:court AS text)))
      AND (
        CAST(:decision_year AS integer) IS NULL
        OR CASE WHEN j.effective_metadata ->> 'year_candidate' ~ '^[0-9]{4}$'
                THEN (j.effective_metadata ->> 'year_candidate')::integer = CAST(:decision_year AS integer)
                ELSE FALSE END
      )
      AND (CAST(:chunk_type AS text) IS NULL OR c.chunk_type = CAST(:chunk_type AS text))
      AND (CAST(:created_after AS timestamptz) IS NULL OR j.created_at >= CAST(:created_after AS timestamptz))
      AND (CAST(:created_before AS timestamptz) IS NULL OR j.created_at < CAST(:created_before AS timestamptz))
),
ranked AS (
    SELECT *,
        ts_rank_cd(search_vector, search_query) AS fts_rank,
        (CASE WHEN exact_phrase THEN 0.35 ELSE 0 END
         + CASE WHEN heading_match THEN 0.20 ELSE 0 END
         + CASE WHEN locator_match THEN 0.50 ELSE 0 END
         + CASE WHEN search_vector @@ search_query THEN 0.25 ELSE 0 END
         + ts_rank_cd(search_vector, search_query)
         + ts_rank_cd(search_vector, fallback_query) * 0.20) AS hybrid_score
    FROM candidates
    WHERE search_vector @@ search_query OR exact_phrase OR locator_match
       OR (search_vector @@ fallback_query AND numnode(fallback_query) >= 1)
)
SELECT chunk_id, job_id, filename, content_sha256, content_type, status,
    source_name, source_url, source_class, metadata_review_status,
    authority_verified, authority_reference, effective_metadata, classification,
    effective_document_type, ordinal, chunk_type, locator, heading,
    page_start, page_end, fts_rank, exact_phrase, heading_match,
    locator_match, hybrid_score,
    ts_headline('simple', body_text,
        CASE WHEN search_vector @@ search_query THEN search_query ELSE fallback_query END,
        'StartSel=<mark>, StopSel=</mark>, MaxWords=45, MinWords=18, ShortWord=2') AS snippet
FROM ranked
ORDER BY hybrid_score DESC, fts_rank DESC, filename ASC, ordinal ASC
LIMIT :limit
""")

def search_legal_chunks_hybrid(
    db: Session, query: str, *, document_type: str | None = None,
    chunk_type: str | None = None, jurisdiction: str | None = None,
    court: str | None = None, decision_year: int | None = None,
    locator: str | None = None, created_after: datetime | None = None,
    created_before: datetime | None = None, limit: int = 20,
    authoritative_only: bool = False,
) -> list[dict]:
    clean_query = (query or "").strip()
    if not clean_query:
        raise ValueError("Search query must not be empty.")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100.")
    if created_after and created_before and created_after >= created_before:
        raise ValueError("created_after must be earlier than created_before.")
    if decision_year is not None and not 1800 <= decision_year <= 2100:
        raise ValueError("decision_year must be between 1800 and 2100.")
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "what", "when",
        "where", "which", "under", "about", "into", "does", "shall", "will",
        "have", "has", "are", "was", "were", "whether", "agreement", "legal",
        "law", "case", "court", "article", "act",
    }
    tokens = []
    for token in re.findall(r"[A-Za-z0-9]+", clean_query.lower()):
        if (len(token) >= 3 or token.isdigit()) and token not in stop_words and token not in tokens:
            tokens.append(token)
        if len(tokens) >= 12:
            break
    if not tokens:
        raise ValueError("Search query must contain at least one meaningful search term.")
    result = db.execute(HYBRID_SEARCH_SQL, {
        "query": clean_query, "fallback_query": " | ".join(tokens),
        "exact_pattern": f"%{clean_query.lower()}%", "document_type": document_type,
        "chunk_type": chunk_type, "jurisdiction": jurisdiction, "court": court,
        "decision_year": decision_year,
        "locator": locator.strip() if locator and locator.strip() else None,
        "created_after": created_after, "created_before": created_before,
        "limit": limit, "authoritative_only": authoritative_only,
    })
    return [dict(row._mapping) for row in result]
