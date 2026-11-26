"""Tenant-scoped due-diligence matters, risk register and comparison records."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.due_diligence import DueDiligenceMatter, DueDiligenceRisk, DocumentComparison
from app.models.tenant import TenantMembership
from app.security.auth import get_current_user

router = APIRouter(prefix="/due-diligence", tags=["due-diligence-risk"])

class MatterCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=3, max_length=300)
    matter_type: str = Field(pattern="^(corporate|transaction|litigation|regulatory|general)$")
    subject_name: str = Field(min_length=2, max_length=300)
    jurisdiction: str = Field(default="India", min_length=2, max_length=120)
    scope: list[str] = Field(default_factory=list, max_length=50)

class RiskCreate(BaseModel):
    category: str = Field(pattern="^(corporate|transaction|litigation|regulatory|contractual|financial|operational|other)$")
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=10, max_length=10000)
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    status: str = Field(default="identified", pattern="^(identified|under_review|mitigating|accepted|closed)$")
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    recommendation: str | None = Field(default=None, max_length=10000)
    mitigation_owner: str | None = Field(default=None, max_length=200)

class ComparisonCreate(BaseModel):
    document_label: str = Field(min_length=2, max_length=300)
    version_a_label: str = Field(min_length=1, max_length=150)
    version_b_label: str = Field(min_length=1, max_length=150)
    changes: list[dict] = Field(min_length=1, max_length=200)
    significance_notes: str | None = Field(default=None, max_length=10000)
    review_status: str = Field(default="pending_review", pattern="^(pending_review|reviewed|revision_required)$")

def _member(db, tenant_id, user_id):
    return db.scalar(select(TenantMembership).where(TenantMembership.tenant_id==tenant_id, TenantMembership.user_id==user_id).limit(1))

def _matter(db, matter_id, user_id):
    return db.scalar(select(DueDiligenceMatter).join(TenantMembership, TenantMembership.tenant_id==DueDiligenceMatter.tenant_id).where(DueDiligenceMatter.id==matter_id, TenantMembership.user_id==user_id))

def _matter_out(x):
    return {"matter_id":x.id,"tenant_id":x.tenant_id,"title":x.title,"matter_type":x.matter_type,
            "subject_name":x.subject_name,"jurisdiction":x.jurisdiction,"scope":json.loads(x.scope_json),
            "status":x.status,"created_at":x.created_at,"updated_at":x.updated_at}

def _risk_out(x):
    score=x.likelihood*x.impact
    return {"risk_id":x.id,"matter_id":x.matter_id,"category":x.category,"title":x.title,
            "description":x.description,"likelihood":x.likelihood,"impact":x.impact,
            "risk_score":score,"severity":x.severity,"status":x.status,
            "evidence_refs":json.loads(x.evidence_refs_json),"recommendation":x.recommendation,
            "mitigation_owner":x.mitigation_owner,"created_at":x.created_at,
            "scoring_note":"Risk score is likelihood × impact on user-entered 1–5 scales; it is a prioritisation aid, not a legal conclusion."}

def _comparison_out(x):
    return {"comparison_id":x.id,"matter_id":x.matter_id,"document_label":x.document_label,
            "version_a_label":x.version_a_label,"version_b_label":x.version_b_label,
            "changes":json.loads(x.changes_json),"significance_notes":x.significance_notes,
            "review_status":x.review_status,"created_at":x.created_at,
            "review_notice":"Changes and significance notes are recorded inputs; legal effect requires human review."}

@router.post("/matters",status_code=201)
def create_matter(p:MatterCreate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=claims.get("app_user_id"); m=_member(db,p.tenant_id,uid) if uid else None
    if not m: raise HTTPException(403,"Workspace membership is required.")
    if m.role=="viewer": raise HTTPException(403,"Viewer role cannot create due-diligence matters.")
    x=DueDiligenceMatter(tenant_id=p.tenant_id,created_by=uid,title=p.title,matter_type=p.matter_type,
       subject_name=p.subject_name,jurisdiction=p.jurisdiction,scope_json=json.dumps(p.scope,ensure_ascii=False))
    db.add(x);db.flush();out=_matter_out(x);db.commit();return out

@router.get("/matters")
def list_matters(tenant_id:str=Query(...),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=claims.get("app_user_id")
    if not uid or not _member(db,tenant_id,uid): raise HTTPException(403,"Workspace membership is required.")
    rows=db.scalars(select(DueDiligenceMatter).where(DueDiligenceMatter.tenant_id==tenant_id).order_by(desc(DueDiligenceMatter.created_at)).limit(limit)).all()
    return {"count":len(rows),"matters":[_matter_out(x) for x in rows]}

@router.get("/matters/{matter_id}")
def get_matter(matter_id:str,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=claims.get("app_user_id");x=_matter(db,matter_id,uid) if uid else None
    if not x: raise HTTPException(404,"Due-diligence matter not found.")
    return _matter_out(x)

@router.post("/matters/{matter_id}/risks",status_code=201)
def add_risk(matter_id:str,p:RiskCreate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=claims.get("app_user_id");matter=_matter(db,matter_id,uid) if uid else None
    if not matter: raise HTTPException(404,"Due-diligence matter not found.")
    membership=_member(db,matter.tenant_id,uid)
    if membership.role=="viewer": raise HTTPException(403,"Viewer role cannot add risks.")
    score=p.likelihood*p.impact
    severity="critical" if score>=20 else "high" if score>=12 else "moderate" if score>=6 else "low"
    x=DueDiligenceRisk(matter_id=matter.id,tenant_id=matter.tenant_id,created_by=uid,
       category=p.category,title=p.title,description=p.description,likelihood=p.likelihood,impact=p.impact,
       severity=severity,status=p.status,evidence_refs_json=json.dumps(p.evidence_refs,ensure_ascii=False),
       recommendation=p.recommendation,mitigation_owner=p.mitigation_owner)
    db.add(x);db.flush();out=_risk_out(x);db.commit();return out

@router.get("/matters/{matter_id}/risks")
def list_risks(matter_id:str,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=claims.get("app_user_id");matter=_matter(db,matter_id,uid) if uid else None
    if not matter: raise HTTPException(404,"Due-diligence matter not found.")
    rows=db.scalars(select(DueDiligenceRisk).where(DueDiligenceRisk.matter_id==matter.id).order_by(desc(DueDiligenceRisk.created_at))).all()
    return {"count":len(rows),"risks":[_risk_out(x) for x in rows]}

@router.post("/matters/{matter_id}/comparisons",status_code=201)
def create_comparison(matter_id:str,p:ComparisonCreate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=claims.get("app_user_id");matter=_matter(db,matter_id,uid) if uid else None
    if not matter: raise HTTPException(404,"Due-diligence matter not found.")
    if _member(db,matter.tenant_id,uid).role=="viewer": raise HTTPException(403,"Viewer role cannot create comparisons.")
    x=DocumentComparison(matter_id=matter.id,tenant_id=matter.tenant_id,created_by=uid,
      document_label=p.document_label,version_a_label=p.version_a_label,version_b_label=p.version_b_label,
      changes_json=json.dumps(p.changes,ensure_ascii=False),significance_notes=p.significance_notes,review_status=p.review_status)
    db.add(x);db.flush();out=_comparison_out(x);db.commit();return out

@router.get("/matters/{matter_id}/comparisons")
def list_comparisons(matter_id:str,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=claims.get("app_user_id");matter=_matter(db,matter_id,uid) if uid else None
    if not matter: raise HTTPException(404,"Due-diligence matter not found.")
    rows=db.scalars(select(DocumentComparison).where(DocumentComparison.matter_id==matter.id).order_by(desc(DocumentComparison.created_at))).all()
    return {"count":len(rows),"comparisons":[_comparison_out(x) for x in rows]}
