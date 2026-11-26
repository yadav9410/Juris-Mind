"""Add persistent background research jobs."""
from alembic import op
import sqlalchemy as sa

revision = "0025_research_jobs"
down_revision = "0024_secure_self_provisioning"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "research_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=100)),
        sa.Column("court", sa.String(length=200)),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(length=48), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("legislation_status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("case_law_status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("snapshot_id", sa.String(length=36)),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_jobs_status_created", "research_jobs", ["status", "created_at"])
    op.create_index("ix_research_jobs_tenant_created", "research_jobs", ["tenant_id", "created_at"])

def downgrade():
    op.drop_index("ix_research_jobs_tenant_created", table_name="research_jobs")
    op.drop_index("ix_research_jobs_status_created", table_name="research_jobs")
    op.drop_table("research_jobs")
