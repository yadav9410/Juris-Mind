"""Add persisted claim-to-evidence assessments.

Revision ID: 0015_claim_evidence_assessments
Revises: 0014_research_agent_runs
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_claim_evidence_assessments"
down_revision = "0014_research_agent_runs"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "research_claim_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("assessment_status", sa.String(40), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("limitations_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_claim_assessment_tenant_created", "research_claim_assessments", ["tenant_id", "created_at"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE research_claim_assessments ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE research_claim_assessments FORCE ROW LEVEL SECURITY")
        op.execute("""
            CREATE POLICY research_claim_assessments_tenant_access
            ON research_claim_assessments
            USING (tenant_id IN (
                SELECT tenant_id FROM tenant_memberships
                WHERE user_id = current_setting('app.user_id', true)
            ))
            WITH CHECK (tenant_id IN (
                SELECT tenant_id FROM tenant_memberships
                WHERE user_id = current_setting('app.user_id', true)
            ))
        """)
        op.execute("GRANT SELECT, INSERT ON TABLE research_claim_assessments TO jurismind_app")

def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS research_claim_assessments_tenant_access ON research_claim_assessments")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE research_claim_assessments FROM jurismind_app")
    op.drop_index("ix_claim_assessment_tenant_created", table_name="research_claim_assessments")
    op.drop_table("research_claim_assessments")
