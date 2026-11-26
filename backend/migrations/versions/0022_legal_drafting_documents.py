"""Tenant-scoped legal drafts and versioned review workflow.
Revision ID: 0022_legal_drafting_documents
Revises: 0021_due_diligence_risk_engine
"""
from alembic import op
import sqlalchemy as sa
revision = "0022_legal_drafting_documents"
down_revision = "0021_due_diligence_risk_engine"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "legal_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column("jurisdiction", sa.String(120), nullable=False, server_default="India"),
        sa.Column("matter_reference", sa.String(100)),
        sa.Column("sections_json", sa.Text(), nullable=False),
        sa.Column("source_refs_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("reviewer_notes", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_legal_drafts_tenant_updated", "legal_drafts", ["tenant_id", "updated_at"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE legal_drafts ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE legal_drafts FORCE ROW LEVEL SECURITY")
        op.execute("""CREATE POLICY legal_drafts_read ON legal_drafts FOR SELECT USING
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=legal_drafts.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true)))""")
        op.execute("""CREATE POLICY legal_drafts_insert ON legal_drafts FOR INSERT WITH CHECK
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=legal_drafts.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))""")
        op.execute("""CREATE POLICY legal_drafts_update ON legal_drafts FOR UPDATE USING
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=legal_drafts.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))
          WITH CHECK (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=legal_drafts.tenant_id
          AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))""")
        op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE legal_drafts TO jurismind_app")

def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for policy in ("legal_drafts_read", "legal_drafts_insert", "legal_drafts_update"):
            op.execute(f"DROP POLICY IF EXISTS {policy} ON legal_drafts")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE legal_drafts FROM jurismind_app")
    op.drop_index("ix_legal_drafts_tenant_updated", table_name="legal_drafts")
    op.drop_table("legal_drafts")
