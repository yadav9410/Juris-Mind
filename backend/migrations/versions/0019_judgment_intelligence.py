"""Evidence-linked structured judgment analysis.
Revision ID: 0019_judgment_intelligence
Revises: 0018_statutory_temporal
"""
from alembic import op
import sqlalchemy as sa
revision = "0019_judgment_intelligence"
down_revision = "0018_statutory_temporal"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "judgment_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ingestion_job_id", sa.String(36), sa.ForeignKey("ingestion_jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_chunk_id", sa.String(36), sa.ForeignKey("ingestion_chunks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("citation", sa.String(300)),
        sa.Column("case_title", sa.String(500), nullable=False),
        sa.Column("court", sa.String(250)),
        sa.Column("decision_date", sa.String(10)),
        sa.Column("bench", sa.JSON(), nullable=False),
        sa.Column("facts", sa.JSON(), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
        sa.Column("arguments_petitioner", sa.JSON(), nullable=False),
        sa.Column("arguments_respondent", sa.JSON(), nullable=False),
        sa.Column("holdings", sa.JSON(), nullable=False),
        sa.Column("ratio_decidendi", sa.Text()),
        sa.Column("final_order", sa.Text()),
        sa.Column("cited_authorities", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False, server_default="pending_review"),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_judgment_analysis_tenant_date", "judgment_analyses", ["tenant_id","decision_date"])
    op.create_index("ix_judgment_analysis_citation", "judgment_analyses", ["citation"])
    bind=op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE judgment_analyses ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE judgment_analyses FORCE ROW LEVEL SECURITY")
        op.execute("""CREATE POLICY judgment_analysis_member_read ON judgment_analyses FOR SELECT USING
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=judgment_analyses.tenant_id
          AND tm.user_id=current_setting('app.user_id', true)))""")
        op.execute("""CREATE POLICY judgment_analysis_member_insert ON judgment_analyses FOR INSERT WITH CHECK
          (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=judgment_analyses.tenant_id
          AND tm.user_id=current_setting('app.user_id', true) AND tm.role IN ('owner','admin','member')))""")
        op.execute("GRANT SELECT, INSERT ON TABLE judgment_analyses TO jurismind_app")

def downgrade():
    bind=op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS judgment_analysis_member_read ON judgment_analyses")
        op.execute("DROP POLICY IF EXISTS judgment_analysis_member_insert ON judgment_analyses")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE judgment_analyses FROM jurismind_app")
    op.drop_index("ix_judgment_analysis_citation", table_name="judgment_analyses")
    op.drop_index("ix_judgment_analysis_tenant_date", table_name="judgment_analyses")
    op.drop_table("judgment_analyses")
