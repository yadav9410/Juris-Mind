"""Add workspace-scoped citation and verification history.
Revision ID: 0012_citation_verification
Revises: 0011_human_metadata_review
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_citation_verification"
down_revision = "0011_human_metadata_review"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "citation_references",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_label", sa.String(300)),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("citation_text", sa.Text(), nullable=False),
        sa.Column("citation_type", sa.String(30), nullable=False),
        sa.Column("normalized_json", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_citation_reference_tenant_created", "citation_references", ["tenant_id", "created_at"])
    op.create_table(
        "verification_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("citation_reference_id", sa.String(36), sa.ForeignKey("citation_references.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_work_id", sa.String(36), sa.ForeignKey("legal_works.id", ondelete="SET NULL")),
        sa.Column("matched_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id", ondelete="SET NULL")),
        sa.Column("pinpoint_status", sa.String(30), nullable=False, server_default="not_applicable"),
        sa.Column("authority_status", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("limitations", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_verification_citation_created", "verification_records", ["citation_reference_id", "created_at"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("citation_references", "verification_records"):
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
        for table in ("verification_records", "citation_references"):
            op.execute(f"DROP POLICY IF EXISTS {table}_tenant_access ON {table}")
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM jurismind_app")
    op.drop_index("ix_verification_citation_created", table_name="verification_records")
    op.drop_table("verification_records")
    op.drop_index("ix_citation_reference_tenant_created", table_name="citation_references")
    op.drop_table("citation_references")
