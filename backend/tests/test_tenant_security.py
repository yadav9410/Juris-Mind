"""Tests for internal identity mapping and tenant membership boundaries."""
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models.tenant import AppUser, Tenant, TenantMembership
from app.security.tenancy import require_tenant_membership

@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()

def test_membership_uses_internal_user_id(db_session):
    external_id = uuid.uuid4()
    user = AppUser(id="jm-user-1", supabase_user_id=external_id, email="member@example.test")
    tenant = Tenant(name="Tenant A")
    db_session.add_all([user, tenant]); db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="admin")); db_session.commit()
    result = require_tenant_membership(tenant.id, {"app_user_id": user.id}, db_session)
    assert result["user_id"] == "jm-user-1" and result["role"] == "admin"

def test_non_member_is_denied(db_session):
    user = AppUser(id="jm-user-2", email="outsider@example.test")
    tenant = Tenant(name="Private Tenant")
    db_session.add_all([user, tenant]); db_session.commit()
    with pytest.raises(HTTPException) as error:
        require_tenant_membership(tenant.id, {"app_user_id": user.id}, db_session)
    assert error.value.status_code == 404

def test_membership_in_one_tenant_does_not_grant_another(db_session):
    user = AppUser(id="jm-user-3", email="limited@example.test")
    a, b = Tenant(name="A"), Tenant(name="B")
    db_session.add_all([user, a, b]); db_session.flush()
    db_session.add(TenantMembership(tenant_id=a.id, user_id=user.id)); db_session.commit()
    with pytest.raises(HTTPException):
        require_tenant_membership(b.id, {"app_user_id": user.id}, db_session)

def test_unmapped_identity_is_not_implicitly_created(db_session):
    assert db_session.query(AppUser).count() == 0
