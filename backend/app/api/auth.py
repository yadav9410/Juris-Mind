"""Authentication lifecycle endpoints for Supabase-backed accounts."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.auth import get_verified_user_claims, get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])

class ProvisionRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    workspace_name: str = Field(default="My JurisMind Workspace", min_length=2, max_length=200)

@router.post("/provision", status_code=201)
def provision_account(
    payload: ProvisionRequest,
    claims: dict = Depends(get_verified_user_claims),
    db: Session = Depends(get_db),
):
    """Provision the caller only, after Supabase JWT verification.

    The database function independently checks the transaction-local verified
    subject set here; callers cannot choose another user's identity.
    """
    if claims.get("is_anonymous") is True:
        raise HTTPException(status_code=403, detail="Anonymous accounts cannot be provisioned")
    token_email = (claims.get("email") or "").strip().lower()
    requested_email = str(payload.email).strip().lower()
    if "@" not in requested_email or requested_email.startswith("@") or requested_email.endswith("@"): 
        raise HTTPException(status_code=422, detail="A valid email address is required")
    if not token_email or token_email != requested_email:
        raise HTTPException(status_code=403, detail="Email does not match the verified Supabase identity")
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.supabase_user_id', :subject, true)"), {"subject": claims["sub"]})
        result = db.execute(text("SELECT * FROM public.provision_jurismind_user(CAST(:subject AS uuid), :email, :workspace_name)"),
            {"subject": claims["sub"], "email": requested_email, "workspace_name": payload.workspace_name}).mappings().one()
        db.commit()
        return {"status": "provisioned", "app_user_id": result["app_user_id"], "tenant_id": result["tenant_id"]}
    raise HTTPException(status_code=503, detail="Account provisioning requires the configured PostgreSQL database")

@router.get("/me")
def account_me(claims: dict = Depends(get_current_user)):
    """Return the authenticated, provisioned JurisMind identity."""
    return {"app_user_id": claims["app_user_id"], "supabase_user_id": claims["supabase_user_id"], "email": claims.get("email")}
