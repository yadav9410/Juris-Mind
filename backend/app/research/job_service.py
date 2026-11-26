"""Queue and execute persistent research jobs."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from app.models.research_job import ResearchJob
from app.search.hybrid import search_legal_chunks_hybrid
from app.sources.external_research import search_official_sources, ExternalSearchNotConfigured


def enqueue_research_job(db: Session, *, tenant_id: str, user_id: str, question: str,
                         jurisdiction: str | None = None, court: str | None = None) -> ResearchJob:
    job = ResearchJob(tenant_id=tenant_id, created_by=user_id, question=question,
                      jurisdiction=jurisdiction, court=court)
    db.add(job)
    db.flush()
    return job


def claim_next_job(db: Session) -> str | None:
    stmt = (select(ResearchJob).where(ResearchJob.status == "queued")
            .order_by(ResearchJob.created_at).limit(1).with_for_update(skip_locked=True))
    job = db.scalar(stmt)
    if job:
        job.status, job.stage = "running", "researching"
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        job_id = job.id
        db.commit()
        return job_id
    return None


def execute_job(session_factory: sessionmaker, job_id: str) -> None:
    """Execute legislation and case-law retrieval concurrently and persist provenance."""
    with session_factory() as db:
        job = db.get(ResearchJob, job_id)
        if not job or job.status not in {"running", "queued"}:
            return
        payload = {"question": job.question, "jurisdiction": job.jurisdiction, "court": job.court}
    try:
        # Search broadly first. Ingestion-time classifications are candidate metadata
        # and may be wrong or awaiting review; they must not hide relevant evidence.
        with session_factory() as search_db:
            retrieved = search_legal_chunks_hybrid(
                search_db, payload["question"], jurisdiction=payload["jurisdiction"],
                court=payload["court"], document_type=None, limit=30
            )

        legislation_types = {"act", "statute", "legislation", "rule", "regulation", "notification"}
        case_types = {"judgment", "judgement", "case", "decision"}
        legislation = []
        cases = []
        other_evidence = []
        for row in retrieved:
            kind = str(row.get("effective_document_type") or "").strip().lower()
            if kind in legislation_types:
                legislation.append(row)
            elif kind in case_types:
                cases.append(row)
            else:
                # Preserve uncertain classifications instead of silently discarding them.
                other_evidence.append(row)

        try:
            external = search_official_sources(
                payload["question"], jurisdiction=payload["jurisdiction"],
                court=payload["court"],
            )
        except ExternalSearchNotConfigured as exc:
            external = {
                "external_search_status": "not_configured", "result_count": 0,
                "document_count": 0, "results": [],
                "configuration_notice": str(exc),
                "verification_status": "not_verified",
            }
        except Exception as exc:
            external = {
                "external_search_status": "provider_error", "result_count": 0,
                "document_count": 0, "results": [],
                "source_errors": [{"error": f"{type(exc).__name__}: {str(exc)[:300]}"}],
                "verification_status": "not_verified",
            }
        result = {
            "legislation": legislation,
            "case_law": cases,
            "other_evidence": other_evidence,
            "retrieved": retrieved,
            "external_research": external,
            "source_scope": "internal_corpus_plus_official_external_sources",
            "external_discovery": external.get("external_search_status", "provider_error"),
            "verification_status": "not_verified",
            "notice": "Internal passages and external official-source results are research leads. Original documents and propositions require legal verification before reliance.",
        }
        with session_factory() as db:
            job = db.get(ResearchJob, job_id)
            job.legislation_status = "completed" if legislation else ("empty" if not retrieved else "not_classified")
            job.case_law_status = "completed" if cases else ("empty" if not retrieved else "not_classified")
            job.stage, job.progress = "evidence_retrieved", 70
            job.result_json = json.dumps(result, default=str, ensure_ascii=False)
            job.status = "completed" if retrieved else "partial"
            job.stage, job.progress = "completed", 100
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as exc:
        with session_factory() as db:
            job = db.get(ResearchJob, job_id)
            if job:
                job.status, job.stage = "failed", "failed"
                job.error_message = str(exc)[:2000]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
