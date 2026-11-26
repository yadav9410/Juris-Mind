"""Tenant membership checks using the internal JurisMind user identity."""
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.tenant import TenantMembership
from app.security.auth import get_current_user

def require_tenant_membership(tenant_id: str, claims: dict = Depends(get_current_user),
                              db: Session = Depends(get_db)) -> dict:
    """Authorize only a provisioned internal user with an actual membership."""
    user_id = claims["app_user_id"]
    membership = db.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id, TenantMembership.user_id == user_id))
    if membership is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"user_id": user_id, "tenant_id": tenant_id, "role": membership.role}
