"""Add workspace-scoped legal research snapshots and evidence records.
Revision ID: 0013_research_snapshots
Revises: 0012_citation_verification
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_research_snapshots"
down_revision = "0012_citation_verification"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "research_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("jurisdiction", sa.String(100)),
        sa.Column("court", sa.String(200)),
        sa.Column("status", sa.String(30), nullable=False, server_default="completed"),
        sa.Column("plan_json", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_research_snapshot_tenant_created",
        "research_snapshots",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_research_snapshot_status",
        "research_snapshots",
        ["status", "created_at"],
    )

    op.create_table(
        "research_snapshot_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_id", sa.String(36), sa.ForeignKey("research_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("sub_question", sa.Text(), nullable=False),
        sa.Column("chunk_id", sa.String(36)),
        sa.Column("job_id", sa.String(36)),
        sa.Column("filename", sa.String(500)),
        sa.Column("locator", sa.String(150)),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_research_evidence_snapshot",
        "research_snapshot_evidence",
        ["snapshot_id", "ordinal"],
    )
    op.create_index(
        "ix_research_evidence_tenant",
        "research_snapshot_evidence",
        ["tenant_id", "snapshot_id"],
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("research_snapshots", "research_snapshot_evidence"):
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
        for table in ("research_snapshot_evidence", "research_snapshots"):
            op.execute(f"DROP POLICY IF EXISTS {table}_tenant_access ON {table}")
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM jurismind_app")
    op.drop_index("ix_research_evidence_tenant", table_name="research_snapshot_evidence")
    op.drop_index("ix_research_evidence_snapshot", table_name="research_snapshot_evidence")
    op.drop_table("research_snapshot_evidence")
    op.drop_index("ix_research_snapshot_status", table_name="research_snapshots")
    op.drop_index("ix_research_snapshot_tenant_created", table_name="research_snapshots")
    op.drop_table("research_snapshots")
