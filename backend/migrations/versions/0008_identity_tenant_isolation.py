"""Link Supabase identities and harden runtime access to identity/membership tables.

Revision ID: 0008_identity_tenant_isolation
Revises: 0007_full_text_search
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_identity_tenant_isolation"
down_revision = "0007_full_text_search"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    op.add_column("app_users", sa.Column("supabase_user_id", sa.Uuid(), nullable=True))
    op.create_index("uq_app_users_supabase_user_id", "app_users", ["supabase_user_id"], unique=True)
    if bind.dialect.name != "postgresql":
        return

    # Runtime roles may read identity and membership records but cannot self-provision
    # accounts or mutate membership/role assignments directly.
    op.execute("REVOKE ALL PRIVILEGES ON TABLE app_users FROM PUBLIC")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE tenant_memberships FROM PUBLIC")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE app_users FROM authenticated, anon")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE tenant_memberships FROM authenticated, anon")
    op.execute("GRANT SELECT ON TABLE app_users, tenant_memberships, tenants TO jurismind_app")

    # Force RLS even for the table owner (unless it has BYPASSRLS/superuser).
    op.execute("ALTER TABLE app_users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app_users FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS app_users_self_access ON app_users")
    op.execute("DROP POLICY IF EXISTS app_users_supabase_identity_lookup ON app_users")
    op.execute("""CREATE POLICY app_users_supabase_identity_lookup ON app_users
        FOR SELECT TO jurismind_app
        USING (supabase_user_id = NULLIF(current_setting('app.supabase_user_id', true), '')::uuid)""")

    op.execute("ALTER TABLE tenant_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_memberships FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS membership_self_access ON tenant_memberships")
    op.execute("DROP POLICY IF EXISTS membership_self_select ON tenant_memberships")
    op.execute("""CREATE POLICY membership_self_select ON tenant_memberships
        FOR SELECT TO jurismind_app
        USING (user_id = NULLIF(current_setting('app.user_id', true), ''))""")

    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_member_access ON tenants")
    op.execute("DROP POLICY IF EXISTS tenant_member_select ON tenants")
    op.execute("""CREATE POLICY tenant_member_select ON tenants
        FOR SELECT TO jurismind_app
        USING (EXISTS (SELECT 1 FROM tenant_memberships m
          WHERE m.tenant_id = tenants.id
            AND m.user_id = NULLIF(current_setting('app.user_id', true), '')))""")

    # Ensure app role has no direct write path to identity or membership tables.
    op.execute("REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON app_users FROM jurismind_app")
    op.execute("REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON tenant_memberships FROM jurismind_app")

def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_member_select ON tenants")
        op.execute("DROP POLICY IF EXISTS membership_self_select ON tenant_memberships")
        op.execute("DROP POLICY IF EXISTS app_users_supabase_identity_lookup ON app_users")
        op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE tenant_memberships DISABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE app_users DISABLE ROW LEVEL SECURITY")
        # Privileges are intentionally not re-granted on downgrade. Restore only via a
        # separately reviewed privilege migration, not an unsafe blanket grant.
    op.drop_index("uq_app_users_supabase_user_id", table_name="app_users")
    op.drop_column("app_users", "supabase_user_id")
