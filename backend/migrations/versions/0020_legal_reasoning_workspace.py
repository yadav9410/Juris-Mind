"""Legal issue and argument reasoning workspaces.
Revision ID: 0020_legal_reasoning_workspace
Revises: 0019_judgment_intelligence
"""
from alembic import op
import sqlalchemy as sa
revision = "0020_legal_reasoning_workspace"
down_revision = "0019_judgment_intelligence"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("legal_reasoning_workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False), sa.Column("fact_summary", sa.Text(), nullable=False),
        sa.Column("linked_snapshot_id", sa.String(36)), sa.Column("linked_assessment_ids_json", sa.Text(), nullable=False),
        sa.Column("issues_json", sa.Text(), nullable=False), sa.Column("arguments_json", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("reviewer_notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_legal_reasoning_tenant_created", "legal_reasoning_workspaces", ["tenant_id", "created_at"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE legal_reasoning_workspaces ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE legal_reasoning_workspaces FORCE ROW LEVEL SECURITY")
        op.execute("""CREATE POLICY legal_reasoning_member_read ON legal_reasoning_workspaces FOR SELECT USING
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=legal_reasoning_workspaces.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true)))""")
        op.execute("""CREATE POLICY legal_reasoning_member_insert ON legal_reasoning_workspaces FOR INSERT WITH CHECK
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=legal_reasoning_workspaces.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))""")
        op.execute("""CREATE POLICY legal_reasoning_member_update ON legal_reasoning_workspaces FOR UPDATE USING
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=legal_reasoning_workspaces.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))
          WITH CHECK (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=legal_reasoning_workspaces.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))""")
        op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE legal_reasoning_workspaces TO jurismind_app")

def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for p in ("legal_reasoning_member_read", "legal_reasoning_member_insert", "legal_reasoning_member_update"):
            op.execute(f"DROP POLICY IF EXISTS {p} ON legal_reasoning_workspaces")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE legal_reasoning_workspaces FROM jurismind_app")
    op.drop_index("ix_legal_reasoning_tenant_created", table_name="legal_reasoning_workspaces")
    op.drop_table("legal_reasoning_workspaces")
