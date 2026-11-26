"""Due diligence matters, risk register and document comparison records.
Revision ID: 0021_due_diligence_risk_engine
Revises: 0020_legal_reasoning_workspace
"""
from alembic import op
import sqlalchemy as sa
revision = "0021_due_diligence_risk_engine"
down_revision = "0020_legal_reasoning_workspace"
branch_labels = None
depends_on = None

def _secure(table, prefix):
    if op.get_bind().dialect.name != "postgresql": return
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"""CREATE POLICY {prefix}_read ON {table} FOR SELECT USING
      (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id={table}.tenant_id
      AND tm.user_id::text=current_setting('app.user_id', true)))""")
    op.execute(f"""CREATE POLICY {prefix}_write ON {table} FOR INSERT WITH CHECK
      (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id={table}.tenant_id
      AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))""")
    op.execute(f"""CREATE POLICY {prefix}_update ON {table} FOR UPDATE USING
      (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id={table}.tenant_id
      AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))
      WITH CHECK (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id={table}.tenant_id
      AND tm.user_id::text=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))""")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON TABLE {table} TO jurismind_app")

def upgrade():
    op.create_table("due_diligence_matters",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("tenant_id",sa.String(36),sa.ForeignKey("tenants.id",ondelete="CASCADE"),nullable=False),
        sa.Column("created_by",sa.String(100),sa.ForeignKey("app_users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("title",sa.String(300),nullable=False),sa.Column("matter_type",sa.String(30),nullable=False),
        sa.Column("subject_name",sa.String(300),nullable=False),sa.Column("jurisdiction",sa.String(120),nullable=False),
        sa.Column("scope_json",sa.Text(),nullable=False),sa.Column("status",sa.String(30),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_dd_matter_tenant_created","due_diligence_matters",["tenant_id","created_at"])
    op.create_table("due_diligence_risks",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("matter_id",sa.String(36),sa.ForeignKey("due_diligence_matters.id",ondelete="CASCADE"),nullable=False),
        sa.Column("tenant_id",sa.String(36),sa.ForeignKey("tenants.id",ondelete="CASCADE"),nullable=False),
        sa.Column("created_by",sa.String(100),sa.ForeignKey("app_users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("category",sa.String(40),nullable=False),sa.Column("title",sa.String(300),nullable=False),
        sa.Column("description",sa.Text(),nullable=False),sa.Column("likelihood",sa.Integer(),nullable=False),
        sa.Column("impact",sa.Integer(),nullable=False),sa.Column("severity",sa.String(20),nullable=False),
        sa.Column("status",sa.String(30),nullable=False),sa.Column("evidence_refs_json",sa.Text(),nullable=False),
        sa.Column("recommendation",sa.Text()),sa.Column("mitigation_owner",sa.String(200)),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_dd_risk_matter","due_diligence_risks",["matter_id","created_at"])
    op.create_table("due_diligence_document_comparisons",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("matter_id",sa.String(36),sa.ForeignKey("due_diligence_matters.id",ondelete="CASCADE"),nullable=False),
        sa.Column("tenant_id",sa.String(36),sa.ForeignKey("tenants.id",ondelete="CASCADE"),nullable=False),
        sa.Column("created_by",sa.String(100),sa.ForeignKey("app_users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("document_label",sa.String(300),nullable=False),sa.Column("version_a_label",sa.String(150),nullable=False),
        sa.Column("version_b_label",sa.String(150),nullable=False),sa.Column("changes_json",sa.Text(),nullable=False),
        sa.Column("significance_notes",sa.Text()),sa.Column("review_status",sa.String(30),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_dd_comparison_matter","due_diligence_document_comparisons",["matter_id","created_at"])
    for table,prefix in [("due_diligence_matters","dd_matter"),("due_diligence_risks","dd_risk"),("due_diligence_document_comparisons","dd_comparison")]:
        _secure(table,prefix)

def downgrade():
    if op.get_bind().dialect.name=="postgresql":
        for table,prefix in [("due_diligence_document_comparisons","dd_comparison"),("due_diligence_risks","dd_risk"),("due_diligence_matters","dd_matter")]:
            for suffix in ("read","write","update"): op.execute(f"DROP POLICY IF EXISTS {prefix}_{suffix} ON {table}")
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM jurismind_app")
    op.drop_index("ix_dd_comparison_matter",table_name="due_diligence_document_comparisons")
    op.drop_table("due_diligence_document_comparisons")
    op.drop_index("ix_dd_risk_matter",table_name="due_diligence_risks")
    op.drop_table("due_diligence_risks")
    op.drop_index("ix_dd_matter_tenant_created",table_name="due_diligence_matters")
    op.drop_table("due_diligence_matters")
