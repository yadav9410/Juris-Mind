"""Add mock-first specialist-agent run and output records.
Revision ID: 0014_research_agent_runs
Revises: 0013_research_snapshots
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_research_agent_runs"
down_revision = "0013_research_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "research_agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_id", sa.String(36), sa.ForeignKey("research_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("initiated_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("execution_mode", sa.String(30), nullable=False, server_default="mock"),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("supervisor_summary", sa.Text(), nullable=False),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_runs_tenant_created", "research_agent_runs", ["tenant_id", "created_at"])
    op.create_index("ix_agent_runs_snapshot", "research_agent_runs", ["snapshot_id", "created_at"])

    op.create_table(
        "research_agent_outputs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("research_agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_key", sa.String(80), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_outputs_run_ordinal", "research_agent_outputs", ["run_id", "ordinal"])
    op.create_index("ix_agent_outputs_tenant", "research_agent_outputs", ["tenant_id", "run_id"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("research_agent_runs", "research_agent_outputs"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(f"""
                CREATE POLICY {table}_tenant_access ON {table}
                USING (tenant_id IN (
                    SELECT tenant_id FROM tenant_memberships
                    WHERE user_id = current_setting('app.user_id', true)
                ))
                WITH CHECK (tenant_id IN (
                    SELECT tenant_id FROM tenant_memberships
                    WHERE user_id = current_setting('app.user_id', true)
                ))
            """)
            op.execute(f"GRANT SELECT, INSERT ON TABLE {table} TO jurismind_app")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("research_agent_outputs", "research_agent_runs"):
            op.execute(f"DROP POLICY IF EXISTS {table}_tenant_access ON {table}")
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM jurismind_app")
    op.drop_index("ix_agent_outputs_tenant", table_name="research_agent_outputs")
    op.drop_index("ix_agent_outputs_run_ordinal", table_name="research_agent_outputs")
    op.drop_table("research_agent_outputs")
    op.drop_index("ix_agent_runs_snapshot", table_name="research_agent_runs")
    op.drop_index("ix_agent_runs_tenant_created", table_name="research_agent_runs")
    op.drop_table("research_agent_runs")
