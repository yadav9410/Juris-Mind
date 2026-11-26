"""Professional platform: matters, tasks, audit events and reports.
Revision ID: 0023_professional_platform
Revises: 0022_legal_drafting_documents
"""
from alembic import op
import sqlalchemy as sa
revision = "0023_professional_platform"
down_revision = "0022_legal_drafting_documents"
branch_labels = None
depends_on = None

def _rls(table, policies):
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    for name, command in policies:
        op.execute(command)

def upgrade():
    op.create_table(
        "platform_matters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("matter_type", sa.String(60), nullable=False, server_default="general"),
        sa.Column("reference", sa.String(120)), sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_platform_matters_tenant_updated", "platform_matters", ["tenant_id","updated_at"])
    op.create_table(
        "platform_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matter_id", sa.String(36), sa.ForeignKey("platform_matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("assigned_to", sa.String(100), sa.ForeignKey("app_users.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(30), nullable=False, server_default="todo"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("due_date", sa.String(10)),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_platform_tasks_matter_status", "platform_tasks", ["matter_id","status"])
    op.create_table(
        "platform_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.String(100), sa.ForeignKey("app_users.id", ondelete="SET NULL")),
        sa.Column("matter_id", sa.String(36), sa.ForeignKey("platform_matters.id", ondelete="SET NULL")),
        sa.Column("entity_type", sa.String(40), nullable=False), sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(60), nullable=False), sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_platform_audit_tenant_created", "platform_audit_events", ["tenant_id","created_at"])
    op.create_table(
        "platform_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matter_id", sa.String(36), sa.ForeignKey("platform_matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("report_type", sa.String(40), nullable=False, server_default="matter_status"),
        sa.Column("title", sa.String(300), nullable=False), sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("quality_status", sa.String(30), nullable=False, server_default="review_required"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_platform_reports_matter_created", "platform_reports", ["matter_id","created_at"])
    if op.get_bind().dialect.name == "postgresql":
        for table in ("platform_matters","platform_tasks","platform_audit_events","platform_reports"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(f"GRANT SELECT, INSERT, UPDATE ON TABLE {table} TO jurismind_app")
        op.execute("GRANT SELECT ON TABLE platform_audit_events TO jurismind_app")
        # Membership-scoped read/write policies. Audit records are insert-only for runtime users.
        for table, name in [("platform_matters","matters"),("platform_tasks","tasks"),("platform_reports","reports")]:
            op.execute(f"""CREATE POLICY {name}_tenant_read ON {table} FOR SELECT USING
              (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id={table}.tenant_id
              AND tm.user_id::text=current_setting('app.user_id', true)))""")
            op.execute(f"""CREATE POLICY {name}_tenant_write ON {table} FOR INSERT WITH CHECK
              (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id={table}.tenant_id
              AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))""")
            op.execute(f"""CREATE POLICY {name}_tenant_update ON {table} FOR UPDATE USING
              (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id={table}.tenant_id
              AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))
              WITH CHECK (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id={table}.tenant_id
              AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))""")
        op.execute("""CREATE POLICY audit_tenant_read ON platform_audit_events FOR SELECT USING
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=platform_audit_events.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true)))""")
        op.execute("""CREATE POLICY audit_tenant_insert ON platform_audit_events FOR INSERT WITH CHECK
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=platform_audit_events.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true)))""")

def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in ("platform_matters","platform_tasks","platform_audit_events","platform_reports"):
            op.execute(f"DROP POLICY IF EXISTS matters_tenant_read ON {table}") if table=="platform_matters" else None
        for table in ("platform_matters","platform_tasks","platform_audit_events","platform_reports"):
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM jurismind_app")
    for table, idx in [("platform_reports","ix_platform_reports_matter_created"),("platform_audit_events","ix_platform_audit_tenant_created"),("platform_tasks","ix_platform_tasks_matter_status"),("platform_matters","ix_platform_matters_tenant_updated")]:
        op.drop_index(idx, table_name=table)
    for table in ("platform_reports","platform_audit_events","platform_tasks","platform_matters"):
        op.drop_table(table)
