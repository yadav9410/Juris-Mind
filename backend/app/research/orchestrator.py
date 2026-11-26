"""Run lexical research queries and persist reproducible snapshots."""
from __future__ import annotations
import json
from typing import Callable
from sqlalchemy.orm import Session
from app.models.research import ResearchSnapshot, ResearchSnapshotEvidence
from app.research.planner import build_research_plan
from app.search.hybrid import search_legal_chunks_hybrid
from app.sources.external_research import search_official_sources, ExternalSearchNotConfigured

SEARCH_NOTICE = (
    "Retrieved passages are research leads, not legal conclusions. Confirm the "
    "original source, applicable version, authority status and pinpoint. "
    "No proposition-to-passage support assessment is performed."
)

def run_research(
    db: Session, *, tenant_id: str, user_id: str, question: str,
    jurisdiction: str | None = None, court: str | None = None,
    document_type: str | None = None, authoritative_only: bool = False,
    supplied_sub_questions: list[str] | None = None,
    per_query_limit: int = 10, search_fn: Callable | None = None,
    external_search_fn: Callable | None = None,
) -> ResearchSnapshot:
    search = search_fn or search_legal_chunks_hybrid
    plan = build_research_plan(question, supplied_sub_questions)
    filters = {
        "jurisdiction": jurisdiction, "court": court,
        "document_type": document_type,
        "authoritative_only": authoritative_only,
        "per_query_limit": per_query_limit,
    }
    snapshot = ResearchSnapshot(
        tenant_id=tenant_id, created_by=user_id, question=question,
        jurisdiction=jurisdiction, court=court, status="running",
        plan_json=json.dumps({
            "original_question": plan.original_question,
            "sub_questions": plan.sub_questions,
            "planning_method": plan.planning_method,
            "planning_notice": plan.planning_notice,
            "retrieval_filters": filters,
        }, ensure_ascii=False),
        summary_json="{}", limitations=SEARCH_NOTICE,
    )
    db.add(snapshot)
    db.flush()
    query_summaries, evidence_ordinal, total_hits = [], 0, 0
    try:
        for sub_question in plan.sub_questions:
            hits = search(
                db, sub_question, jurisdiction=jurisdiction, court=court,
                document_type=document_type,
                authoritative_only=authoritative_only,
                limit=per_query_limit,
            )
            query_summaries.append({"sub_question": sub_question, "result_count": len(hits)})
            for hit in hits:
                evidence_ordinal += 1
                total_hits += 1
                db.add(ResearchSnapshotEvidence(
                    snapshot_id=snapshot.id, tenant_id=tenant_id,
                    ordinal=evidence_ordinal, sub_question=sub_question,
                    chunk_id=str(hit.get("chunk_id")) if hit.get("chunk_id") is not None else None,
                    job_id=str(hit.get("job_id")) if hit.get("job_id") is not None else None,
                    filename=hit.get("filename"), locator=hit.get("locator"),
                    page_start=hit.get("page_start"), page_end=hit.get("page_end"),
                    evidence_json=json.dumps(dict(hit), default=str, ensure_ascii=False),
                ))
        # Run official-domain external research as part of the same user-facing
        # snapshot workflow. Missing provider configuration is explicit and does
        # not block the internal corpus research.
        try:
            external_search = external_search_fn or search_official_sources
            external = external_search(
                question, jurisdiction=jurisdiction, court=court,
            )
        except ExternalSearchNotConfigured as exc:
            external = {
                "external_search_status": "not_configured", "result_count": 0,
                "document_count": 0, "results": [],
                "configuration_notice": str(exc), "verification_status": "not_verified",
            }
        except Exception as exc:
            external = {
                "external_search_status": "provider_error", "result_count": 0,
                "document_count": 0, "results": [],
                "source_errors": [{"error": f"{type(exc).__name__}: {str(exc)[:300]}"}],
                "verification_status": "not_verified",
            }

        external_results = external.get("results", [])
        for item in external_results:
            evidence_ordinal += 1
            locator = None
            pages = item.get("page_evidence") or []
            if pages:
                locator = f"Page {pages[0].get('page')}"
            db.add(ResearchSnapshotEvidence(
                snapshot_id=snapshot.id, tenant_id=tenant_id,
                ordinal=evidence_ordinal, sub_question=question,
                chunk_id=None, job_id=None,
                filename=item.get("title") or item.get("source_name"),
                locator=locator, page_start=(pages[0].get("page") if pages else None),
                page_end=(pages[-1].get("page") if pages else None),
                evidence_json=json.dumps({
                    **item, "evidence_type": "external_official_source",
                }, default=str, ensure_ascii=False),
            ))

        snapshot.status = "completed"
        snapshot.summary_json = json.dumps({
            "query_count": len(plan.sub_questions), "result_count": total_hits,
            "external_result_count": external.get("result_count", len(external_results)),
            "external_document_count": external.get("document_count", 0),
            "external_search_status": external.get("external_search_status", "unknown"),
            "external_research": external,
            "queries": query_summaries,
            "retrieval_method": "PostgreSQL hybrid lexical search plus official-domain external search",
            "semantic_vectors_enabled": False, "retrieval_filters": filters,
            "evidence_ready": total_hits > 0 or bool(external_results),
            "evidence_state": "retrieved" if (total_hits or external_results) else "no_search_matches",
            "next_action": (
                "Review internal passages and external original documents; confirm applicable version, authority status and proposition support."
                if (total_hits or external_results) else
                "Check corpus readiness, external-search provider configuration, and search terms before creating a new snapshot."
            ),
        }, ensure_ascii=False)
        db.flush()
        return snapshot
    except Exception:
        snapshot.status = "failed"
        snapshot.summary_json = json.dumps({
            "query_count": len(query_summaries), "result_count": total_hits,
            "queries": query_summaries, "retrieval_filters": filters,
        }, ensure_ascii=False)
        db.flush()
        raise
