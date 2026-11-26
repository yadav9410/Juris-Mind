"""Small protected example endpoint for testing tenant authorization."""

from fastapi import APIRouter, Depends
from app.security.tenancy import require_tenant_membership

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/{tenant_id}/access-check")
def tenant_access_check(access: dict = Depends(require_tenant_membership)):
    """Return the caller's membership only after server-side authorization."""
    return {"access": "granted", **access}
