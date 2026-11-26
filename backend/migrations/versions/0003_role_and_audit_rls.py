"""Harden workspace roles and protect tenant-scoped audit events.

This migration deliberately leaves public legal-corpus tables globally readable.
SQLite skips PostgreSQL-specific policies and constraints.
"""
from alembic import op

revision = "0003_role_audit_rls"
down_revision = "0002_tenant_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    # Limit roles to the four supported workspace roles.
    op.execute("""
        ALTER TABLE tenant_memberships
        ADD CONSTRAINT ck_membership_role
        CHECK (role IN ('owner', 'admin', 'member', 'viewer'))
    """)

    # Audit events are private when attached to a tenant. Global events
    # (tenant_id IS NULL) remain outside this tenant-specific policy.
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_audit_access ON audit_events
        USING (
            tenant_id IS NOT NULL AND EXISTS (
                SELECT 1 FROM tenant_memberships m
                WHERE m.tenant_id = audit_events.tenant_id
                  AND m.user_id = current_setting('app.user_id', true)
            )
        )
        WITH CHECK (
            tenant_id IS NOT NULL AND EXISTS (
                SELECT 1 FROM tenant_memberships m
                WHERE m.tenant_id = audit_events.tenant_id
                  AND m.user_id = current_setting('app.user_id', true)
            )
        )
    """)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP POLICY IF EXISTS tenant_audit_access ON audit_events")
    op.execute("ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_memberships DROP CONSTRAINT IF EXISTS ck_membership_role")
