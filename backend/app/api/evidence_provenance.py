"""Workspace-scoped verification of evidence against ingested source records."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.session import get_db
from app.evidence.provenance import verify_chunk_evidence
from app.models.evidence import EvidenceVerification
from app.models.tenant import TenantMembership
from app.security.auth import get_current_user

router = APIRouter(prefix="/research/evidence", tags=["evidence-provenance-integrity"])

class EvidenceVerificationRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    chunk_id: str = Field(min_length=1, max_length=36)
    expected_page: int | None = Field(default=None, ge=1)
    expected_locator: str | None = Field(default=None, max_length=150)
    supplied_text: str | None = Field(default=None, min_length=1, max_length=20000)

def _membership(db: Session, tenant_id: str, user_id: str):
    return db.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.user_id == user_id,
    ).limit(1))

@router.post("/verify", status_code=201)
def create_evidence_verification(
    payload: EvidenceVerificationRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user),
):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    membership = _membership(db, payload.tenant_id, user_id)
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of the requested workspace.")
    if membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewer role cannot create evidence verifications.")

    result = verify_chunk_evidence(
        db, chunk_id=payload.chunk_id,
        storage_root=get_settings().ingestion_storage_dir,
        expected_page=payload.expected_page,
        expected_locator=payload.expected_locator,
        supplied_text=payload.supplied_text,
    )
    chunk, job = result["chunk"], result["job"]
    if chunk is not None and job is not None and job.status not in {"extracted", "needs_ocr"}:
        result["status"] = "unresolved"
        result["reasons"].append("The ingestion job is not in an extractable state.")
    record = EvidenceVerification(
        tenant_id=membership.tenant_id, created_by=user_id,
        job_id=job.id if job else "unresolved",
        chunk_id=chunk.id if chunk else payload.chunk_id,
        status=result["status"], integrity_status=result["integrity_status"],
        locator_status=result["locator_status"], text_status=result["text_status"],
        stored_document_sha256=result["stored_document_sha256"] or "",
        observed_document_sha256=result["observed_document_sha256"],
        chunk_text_sha256=result["chunk_text_sha256"] or "",
        source_name=job.source_name if job else None,
        source_url=job.source_url if job else None,
        source_class=job.source_class if job else "unverified",
        page_start=chunk.page_start if chunk else None,
        page_end=chunk.page_end if chunk else None,
        locator=chunk.locator if chunk else None,
        reasons_json=json.dumps(result["reasons"], ensure_ascii=False),
        authenticity_status="not_independently_authenticated",
    )
    db.add(record)
    # Flush assigns database/client defaults while the authenticated transaction
    # and its transaction-local RLS identity context are still active.
    db.flush()
    response_payload = _serialize(record)
    # Commit only after serialization. With expire_on_commit=True, serializing
    # the ORM instance after commit would trigger a reload in a new transaction;
    # transaction-local RLS context is then gone and PostgreSQL may hide the row.
    db.commit()
    return response_payload

def _serialize(record: EvidenceVerification):
    return {
        "verification_id": record.id, "tenant_id": record.tenant_id,
        "job_id": record.job_id, "chunk_id": record.chunk_id,
        "status": record.status, "integrity_status": record.integrity_status,
        "locator_status": record.locator_status, "text_status": record.text_status,
        "stored_document_sha256": record.stored_document_sha256 or None,
        "observed_document_sha256": record.observed_document_sha256,
        "chunk_text_sha256": record.chunk_text_sha256 or None,
        "source": {"source_name": record.source_name, "source_url": record.source_url,
                   "source_class": record.source_class},
        "locator": {"page_start": record.page_start, "page_end": record.page_end,
                    "locator": record.locator},
        "authenticity_status": record.authenticity_status,
        "reasons": json.loads(record.reasons_json),
        "created_at": record.created_at,
        "notice": "File integrity and repository linkage do not independently authenticate the publisher or establish legal authority or proposition support.",
    }

@router.get("/{verification_id}")
def get_evidence_verification(
    verification_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user),
):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    record = db.scalar(
        select(EvidenceVerification)
        .join(TenantMembership, TenantMembership.tenant_id == EvidenceVerification.tenant_id)
        .where(EvidenceVerification.id == verification_id,
               TenantMembership.user_id == user_id)
    )
    if not record:
        raise HTTPException(status_code=404, detail="Evidence verification not found.")
    return _serialize(record)
