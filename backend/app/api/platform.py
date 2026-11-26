"""Professional matter/workflow platform APIs and integrated review reporting."""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.platform import PlatformMatter, PlatformTask, PlatformAuditEvent, PlatformReport
from app.models.tenant import TenantMembership
from app.models.drafting import LegalDraft
from app.models.research import ResearchSnapshot
from app.models.agent import ResearchAgentRun, ResearchAgentOutput
from app.security.auth import get_current_user

router = APIRouter(prefix="/platform", tags=["jurismind-professional-platform"])
MATTER_STATES = {"open", "in_progress", "on_hold", "closed"}
TASK_STATES = {"todo", "in_progress", "blocked", "completed", "cancelled"}
PRIORITIES = {"low", "normal", "high", "urgent"}

class MatterCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=3, max_length=300)
    matter_type: str = Field(default="general", max_length=60)
    reference: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=10000)

class MatterUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    status: str | None = None

class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to: str | None = None
    priority: str = "normal"
    due_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

class TaskUpdate(BaseModel):
    assigned_to: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

class ReviewRunRequest(BaseModel):
    snapshot_id: str = Field(min_length=1, max_length=36)
    selected_agents: list[str] | None = Field(default=None, max_length=10)
    execution_mode: str = "mock"

def _uid(claims):
    return claims.get("app_user_id")

def _member(db, tenant_id, uid):
    if not uid: return None
    return db.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.user_id == uid).limit(1))

def _matter(db, matter_id, uid):
    return db.scalar(select(PlatformMatter).join(TenantMembership,
        TenantMembership.tenant_id == PlatformMatter.tenant_id).where(
        PlatformMatter.id == matter_id, TenantMembership.user_id == uid))

def _audit(db, tenant_id, uid, matter_id, entity_type, entity_id, action, details=None):
    db.add(PlatformAuditEvent(tenant_id=tenant_id, actor_user_id=uid, matter_id=matter_id,
        entity_type=entity_type, entity_id=entity_id, action=action,
        details_json=json.dumps(details or {}, ensure_ascii=False)))

def _matter_payload(row):
    return {"matter_id": row.id, "tenant_id": row.tenant_id, "title": row.title,
        "matter_type": row.matter_type, "reference": row.reference,
        "description": row.description, "status": row.status,
        "created_at": row.created_at, "updated_at": row.updated_at}

@router.post("/matters", status_code=201)
def create_matter(p: MatterCreate, db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    uid = _uid(claims); member = _member(db, p.tenant_id, uid)
    if not member: raise HTTPException(403, "Workspace membership is required.")
    if member.role == "viewer": raise HTTPException(403, "Viewer role cannot create matters.")
    row = PlatformMatter(tenant_id=p.tenant_id, created_by=uid, title=p.title,
        matter_type=p.matter_type, reference=p.reference, description=p.description)
    db.add(row); db.flush()
    _audit(db,p.tenant_id,uid,row.id,"matter",row.id,"created",{"title":row.title})
    result=_matter_payload(row); db.commit(); return result

@router.get("/matters")
def list_matters(tenant_id: str = Query(...), limit: int = Query(50,ge=1,le=100),
                 db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    uid=_uid(claims)
    if not _member(db,tenant_id,uid): raise HTTPException(403,"Workspace membership is required.")
    rows=db.scalars(select(PlatformMatter).where(PlatformMatter.tenant_id==tenant_id)
        .order_by(desc(PlatformMatter.updated_at)).limit(limit)).all()
    return {"count":len(rows),"matters":[_matter_payload(r) for r in rows]}

@router.get("/matters/{matter_id}")
def get_matter(matter_id: str, db: Session=Depends(get_db), claims: dict=Depends(get_current_user)):
    row=_matter(db,matter_id,_uid(claims))
    if not row: raise HTTPException(404,"Matter not found.")
    tasks=db.scalars(select(PlatformTask).where(PlatformTask.matter_id==row.id)
        .order_by(desc(PlatformTask.updated_at))).all()
    return {**_matter_payload(row),"tasks":[_task_payload(t) for t in tasks]}

@router.patch("/matters/{matter_id}")
def update_matter(matter_id: str,p:MatterUpdate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=_uid(claims); row=_matter(db,matter_id,uid)
    if not row: raise HTTPException(404,"Matter not found.")
    member=_member(db,row.tenant_id,uid)
    if member.role=="viewer": raise HTTPException(403,"Viewer role cannot update matters.")
    data=p.model_dump(exclude_unset=True)
    if data.get("status") is not None and data["status"] not in MATTER_STATES:
        raise HTTPException(422,"Invalid matter status.")
    for key in ("title","description","status"):
        if key in data and data[key] is not None: setattr(row,key,data[key])
    row.updated_at=datetime.now(timezone.utc)
    _audit(db,row.tenant_id,uid,row.id,"matter",row.id,"updated",data)
    result=_matter_payload(row); db.commit(); return result

def _task_payload(t):
    return {"task_id":t.id,"matter_id":t.matter_id,"title":t.title,"description":t.description,
        "assigned_to":t.assigned_to,"status":t.status,"priority":t.priority,"due_date":t.due_date,
        "created_at":t.created_at,"updated_at":t.updated_at}

@router.post("/matters/{matter_id}/tasks",status_code=201)
def create_task(matter_id:str,p:TaskCreate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=_uid(claims); matter=_matter(db,matter_id,uid)
    if not matter: raise HTTPException(404,"Matter not found.")
    member=_member(db,matter.tenant_id,uid)
    if member.role=="viewer": raise HTTPException(403,"Viewer role cannot create tasks.")
    if p.priority not in PRIORITIES: raise HTTPException(422,"Invalid priority.")
    if p.assigned_to and not _member(db,matter.tenant_id,p.assigned_to):
        raise HTTPException(422,"Assignee must be a member of this workspace.")
    row=PlatformTask(tenant_id=matter.tenant_id,matter_id=matter.id,title=p.title,
        description=p.description,assigned_to=p.assigned_to,priority=p.priority,due_date=p.due_date,created_by=uid)
    db.add(row); db.flush()
    _audit(db,matter.tenant_id,uid,matter.id,"task",row.id,"created",{"title":row.title})
    result=_task_payload(row); db.commit(); return result

@router.patch("/tasks/{task_id}")
def update_task(task_id:str,p:TaskUpdate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=_uid(claims)
    row=db.scalar(select(PlatformTask).join(TenantMembership,TenantMembership.tenant_id==PlatformTask.tenant_id)
        .where(PlatformTask.id==task_id,TenantMembership.user_id==uid))
    if not row: raise HTTPException(404,"Task not found.")
    member=_member(db,row.tenant_id,uid)
    if member.role=="viewer": raise HTTPException(403,"Viewer role cannot update tasks.")
    data=p.model_dump(exclude_unset=True)
    if data.get("status") is not None and data["status"] not in TASK_STATES: raise HTTPException(422,"Invalid task status.")
    if data.get("priority") is not None and data["priority"] not in PRIORITIES: raise HTTPException(422,"Invalid task priority.")
    if data.get("assigned_to") and not _member(db,row.tenant_id,data["assigned_to"]):
        raise HTTPException(422,"Assignee must be a member of this workspace.")
    for k,v in data.items(): setattr(row,k,v)
    row.updated_at=datetime.now(timezone.utc)
    _audit(db,row.tenant_id,uid,row.matter_id,"task",row.id,"updated",data)
    result=_task_payload(row); db.commit(); return result

@router.get("/matters/{matter_id}/audit")
def list_audit(matter_id:str,limit:int=Query(100,ge=1,le=250),db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=_uid(claims); matter=_matter(db,matter_id,uid)
    if not matter: raise HTTPException(404,"Matter not found.")
    rows=db.scalars(select(PlatformAuditEvent).where(PlatformAuditEvent.matter_id==matter_id)
        .order_by(desc(PlatformAuditEvent.created_at)).limit(limit)).all()
    return {"count":len(rows),"events":[{"event_id":r.id,"actor_user_id":r.actor_user_id,
        "entity_type":r.entity_type,"entity_id":r.entity_id,"action":r.action,
        "details":json.loads(r.details_json),"created_at":r.created_at} for r in rows]}

@router.post("/matters/{matter_id}/agent-review")
def agent_review(matter_id:str,p:ReviewRunRequest,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=_uid(claims); matter=_matter(db,matter_id,uid)
    if not matter: raise HTTPException(404,"Matter not found.")
    if p.execution_mode not in {"mock","openai"}: raise HTTPException(422,"execution_mode must be mock or openai.")
    if p.execution_mode=="openai":
        raise HTTPException(400,"OpenAI execution is not enabled through this platform endpoint. Use the existing agent workflow endpoint and its explicit configuration.")
    snapshot=db.scalar(select(ResearchSnapshot).where(ResearchSnapshot.id==p.snapshot_id,
        ResearchSnapshot.tenant_id==matter.tenant_id))
    if not snapshot: raise HTTPException(404,"Research snapshot not found in this workspace.")
    from app.agents.supervisor import run_supervisor
    try:
        run=run_supervisor(db,snapshot=snapshot,user_id=uid,selected_agents=p.selected_agents,execution_mode="mock")
    except ValueError as exc: raise HTTPException(422,str(exc))
    _audit(db,matter.tenant_id,uid,matter.id,"agent_review",run.id,"completed",{"snapshot_id":snapshot.id,"status":run.status})
    db.commit()
    outputs=db.scalars(select(ResearchAgentOutput).where(ResearchAgentOutput.run_id==run.id).order_by(ResearchAgentOutput.ordinal)).all()
    return {"run_id":run.id,"status":run.status,"supervisor_summary":run.supervisor_summary,
        "limitations":run.limitations,"outputs":[json.loads(o.output_json) for o in outputs]}

@router.post("/matters/{matter_id}/quality-report",status_code=201)
def create_quality_report(matter_id:str,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    uid=_uid(claims); matter=_matter(db,matter_id,uid)
    if not matter: raise HTTPException(404,"Matter not found.")
    tasks=db.scalars(select(PlatformTask).where(PlatformTask.matter_id==matter.id)).all()
    drafts=db.scalars(select(LegalDraft).where(LegalDraft.tenant_id==matter.tenant_id,
        LegalDraft.matter_reference==matter.reference if matter.reference else LegalDraft.matter_reference.is_(None))).all()
    open_tasks=[t for t in tasks if t.status not in {"completed","cancelled"}]
    checks=[
        {"check":"Matter has a description","passed":bool(matter.description),"severity":"advisory"},
        {"check":"All matter tasks completed or cancelled","passed":not open_tasks,"severity":"review"},
        {"check":"At least one draft associated with matter reference","passed":bool(drafts),"severity":"advisory"},
        {"check":"Drafts have human review status","passed":all(d.status in {"reviewed","final"} for d in drafts) if drafts else False,"severity":"review"},
    ]
    status="ready_for_human_review" if all(c["passed"] for c in checks) else "review_required"
    content={"matter":_matter_payload(matter),"task_count":len(tasks),"open_task_count":len(open_tasks),
        "draft_count":len(drafts),"checks":checks,
        "limitations":["Automated completeness checks do not determine legal correctness or sufficiency.",
        "Source authenticity, citation accuracy, currentness and legal conclusions require human verification."]}
    row=PlatformReport(tenant_id=matter.tenant_id,matter_id=matter.id,created_by=uid,
        report_type="quality_assurance",title=f"Quality Review — {matter.title}",
        content_json=json.dumps(content,ensure_ascii=False),quality_status=status)
    db.add(row);db.flush()
    _audit(db,matter.tenant_id,uid,matter.id,"report",row.id,"created",{"quality_status":status})
    result={"report_id":row.id,"title":row.title,"quality_status":status,"content":content}
    db.commit();return result

@router.get("/matters/{matter_id}/reports")
def list_reports(matter_id:str,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    matter=_matter(db,matter_id,_uid(claims))
    if not matter: raise HTTPException(404,"Matter not found.")
    rows=db.scalars(select(PlatformReport).where(PlatformReport.matter_id==matter.id)
        .order_by(desc(PlatformReport.created_at))).all()
    return {"count":len(rows),"reports":[{"report_id":r.id,"title":r.title,
        "report_type":r.report_type,"quality_status":r.quality_status,
        "content":json.loads(r.content_json),"created_at":r.created_at} for r in rows]}
