"""Initial multi-tenant database models.

These tables establish the data relationships. They do NOT, by themselves,
provide complete tenant security. Authorization checks and PostgreSQL RLS
must be added and tested before private documents are used.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for audit-friendly records."""
    return datetime.now(timezone.utc)


class Tenant(Base):
    """A workspace that owns private research and uploaded documents."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # A tenant can have multiple user memberships.
    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="tenant")


class AppUser(Base):
    """Local application profile linked later to a Supabase Auth user ID."""

    __tablename__ = "app_users"

    # Internal JurisMind identity. Never use a JWT subject directly as this ID.
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    # Set only by trusted provisioning after verifying the Supabase identity.
    supabase_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="user")


class TenantMembership(Base):
    """Connects a user to a tenant and records their workspace role."""

    __tablename__ = "tenant_memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="member", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    tenant: Mapped["Tenant"] = relationship(back_populates="memberships")
    user: Mapped["AppUser"] = relationship(back_populates="memberships")
