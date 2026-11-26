"""Human review controls for the shared staged legal corpus."""
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ingestion import IngestionJob, MetadataReviewEvent
from app.models.tenant import TenantMembership
from app.security.auth import get_current_user

router = APIRouter(prefix="/metadata-review", tags=["metadata-review"])


class ReviewDecision(BaseModel):
    action: Literal["approve", "correct", "reject"]
    corrected_metadata: dict | None = None
    note: str | None = Field(default=None, max_length=4000)
    authority_verified: bool = False
    authority_reference: str | None = Field(default=None, max_length=2000)
    authority_evidence: str | None = Field(default=None, max_length=8000)

    @model_validator(mode="after")
    def validate_decision(self):
        if self.action == "correct" and not self.corrected_metadata:
            raise ValueError("corrected_metadata is required for a correction.")
        if self.action != "correct" and self.corrected_metadata is not None:
            raise ValueError("corrected_metadata is only valid for action='correct'.")
        if self.authority_verified and (not self.authority_reference or not self.authority_evidence):
            raise ValueError("Authority verification requires a reference and evidence note.")
        if self.action == "reject" and self.authority_verified:
            raise ValueError("A rejected document cannot be authority-verified.")
        return self


def require_reviewer(claims: dict, db: Session) -> str:
    """Only workspace owners/admins may review the shared legal corpus."""
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Reviewer identity is unavailable.")
    allowed = db.scalar(select(TenantMembership.id).where(
        TenantMembership.user_id == user_id,
        TenantMembership.role.in_(("owner", "admin")),
    ).limit(1))
    if not allowed:
        raise HTTPException(status_code=403, detail="Workspace owner or admin role required.")
    return user_id


@router.get("/queue")
def review_queue(
    limit: int = 50,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user),
):
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200.")
    require_reviewer(claims, db)
    jobs = db.scalars(select(IngestionJob).where(
        IngestionJob.metadata_review_status == "pending",
        IngestionJob.status.in_(("extracted", "needs_ocr")),
    ).order_by(IngestionJob.created_at.asc()).limit(limit)).all()
    return {"count": len(jobs), "items": [{
        "job_id": j.id, "filename": j.filename, "metadata_candidates": json.loads(j.metadata_json) if j.metadata_json else None,
        "source_name": j.source_name, "source_url": j.source_url, "source_class": j.source_class,
        "authority_verified": j.authority_verified,
    } for j in jobs]}


@router.post("/jobs/{job_id}/decision")
def decide_metadata(
    job_id: str,
    decision: ReviewDecision,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user),
):
    reviewer_id = require_reviewer(claims, db)
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    if job.status not in {"extracted", "needs_ocr"}:
        raise HTTPException(status_code=409, detail="Only successfully extracted jobs can be reviewed.")
    if job.metadata_review_status in {"approved", "corrected", "rejected"}:
        raise HTTPException(status_code=409, detail="This record has already been reviewed. Use a new review workflow to amend it.")
    previous = job.metadata_json
    candidates = json.loads(job.metadata_json) if job.metadata_json else {}
    if decision.action == "approve":
        resulting = candidates
        job.metadata_review_status = "approved"
    elif decision.action == "correct":
        resulting = decision.corrected_metadata
        job.metadata_review_status = "corrected"
    else:
        resulting = None
        job.metadata_review_status = "rejected"

    verified = bool(decision.authority_verified)
    if verified:
        if decision.action not in {"approve", "correct"}:
            raise HTTPException(status_code=422, detail="Only approved or corrected metadata can be authority-verified.")
        if job.source_class != "primary":
            raise HTTPException(status_code=422, detail="Authority verification requires source_class='primary'.")
        job.authority_verified_at = datetime.now(timezone.utc)
        job.authority_verified_by = reviewer_id
        job.authority_reference = decision.authority_reference
        job.authority_evidence = decision.authority_evidence
    else:
        job.authority_verified_at = None
        job.authority_verified_by = None
        job.authority_reference = None
        job.authority_evidence = None
    job.authority_verified = verified
    job.reviewed_metadata_json = json.dumps(resulting, ensure_ascii=False) if resulting is not None else None

    db.add(MetadataReviewEvent(
        job_id=job.id, reviewer_user_id=reviewer_id, action=decision.action,
        previous_metadata_json=previous,
        resulting_metadata_json=job.reviewed_metadata_json,
        authority_verified=verified, note=decision.note,
    ))
    db.commit()
    return {
        "job_id": job.id, "metadata_review_status": job.metadata_review_status,
        "reviewed_metadata": resulting, "authority_verified": job.authority_verified,
        "authority_reference": job.authority_reference,
        "notice": "Metadata review and authority verification are separate determinations. Verify source authenticity and legal status independently.",
    }
