"""Add PostgreSQL row-level security for tenant and membership records.

SQLite is intentionally skipped: it does not implement PostgreSQL RLS.
"""
from alembic import op

revision = "0002_tenant_rls"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Membership rows are visible only to the authenticated user set by the API.
    op.execute("ALTER TABLE tenant_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_memberships FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY membership_self_access ON tenant_memberships
        USING (user_id = current_setting('app.user_id', true))
        WITH CHECK (user_id = current_setting('app.user_id', true))
    """)

    # A tenant is visible only if the current user has a membership in it.
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_member_access ON tenants
        USING (EXISTS (
            SELECT 1 FROM tenant_memberships m
            WHERE m.tenant_id = tenants.id
              AND m.user_id = current_setting('app.user_id', true)
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM tenant_memberships m
            WHERE m.tenant_id = tenants.id
              AND m.user_id = current_setting('app.user_id', true)
        ))
    """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP POLICY IF EXISTS tenant_member_access ON tenants")
    op.execute("DROP POLICY IF EXISTS membership_self_access ON tenant_memberships")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_memberships DISABLE ROW LEVEL SECURITY")
