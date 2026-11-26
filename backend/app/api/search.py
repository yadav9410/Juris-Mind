"""Authenticated API endpoints for staged legal-passage discovery."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.search.hybrid import search_legal_chunks_hybrid
from app.security.auth import get_current_user

router = APIRouter(prefix="/search", tags=["legal-search"])

SEARCH_NOTICE = (
    "Discovery results only. Classification and ranking are heuristic; "
    "verify the original source, legal status, and pinpoint before legal reliance."
)

@router.get("/hybrid")
def hybrid_search(
    q: str = Query(..., min_length=1, max_length=500),
    document_type: str | None = Query(None, max_length=40),
    chunk_type: str | None = Query(None, max_length=40),
    jurisdiction: str | None = Query(None, max_length=100),
    court: str | None = Query(None, max_length=200),
    decision_year: int | None = Query(None, ge=1800, le=2200),
    locator: str | None = Query(None, max_length=150),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
    authoritative_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _claims: dict = Depends(get_current_user),
):
    """Find staged passages using FTS, phrase, heading and locator signals."""
    try:
        hits = search_legal_chunks_hybrid(
            db, q, document_type=document_type, chunk_type=chunk_type,
            jurisdiction=jurisdiction, court=court, decision_year=decision_year,
            locator=locator, created_after=created_after,
            created_before=created_before, limit=limit, authoritative_only=authoritative_only,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Hybrid search requires PostgreSQL and the staged-chunk search index.",
        ) from exc
    return {
        "query": q,
        "count": len(hits),
        "results": hits,
        "ranking": "PostgreSQL full-text + exact phrase + heading + locator",
        "metadata_filters": {"jurisdiction": jurisdiction, "court": court, "decision_year": decision_year},
        "semantic_vectors_enabled": False,
        "authoritative_only": authoritative_only,
        "notice": SEARCH_NOTICE,
    }

@router.get("/full-text", include_in_schema=False)
def full_text_compatibility(
    q: str = Query(..., min_length=1, max_length=500),
    document_type: str | None = Query(None, max_length=40),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _claims: dict = Depends(get_current_user),
):
    """Backward-compatible path; delegates to the hybrid lexical ranker."""
    try:
        hits = search_legal_chunks_hybrid(db, q, document_type=document_type, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Search requires PostgreSQL and the staged-chunk search index.") from exc
    return {"query": q, "count": len(hits), "results": hits, "notice": SEARCH_NOTICE}
