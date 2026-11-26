"""Add persisted evidence provenance and original-file integrity verification.

Revision ID: 0016_evidence_integrity
Revises: 0015_claim_evidence_assessments
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_evidence_integrity"
down_revision = "0015_claim_evidence_assessments"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "evidence_verifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("chunk_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("integrity_status", sa.String(30), nullable=False),
        sa.Column("locator_status", sa.String(30), nullable=False),
        sa.Column("text_status", sa.String(30), nullable=False),
        sa.Column("stored_document_sha256", sa.String(64), nullable=False),
        sa.Column("observed_document_sha256", sa.String(64)),
        sa.Column("chunk_text_sha256", sa.String(64), nullable=False),
        sa.Column("source_name", sa.String(200)),
        sa.Column("source_url", sa.Text()),
        sa.Column("source_class", sa.String(30), nullable=False),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("locator", sa.String(150)),
        sa.Column("reasons_json", sa.Text(), nullable=False),
        sa.Column("authenticity_status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_verification_tenant_created", "evidence_verifications", ["tenant_id", "created_at"])
    op.create_index("ix_evidence_verification_chunk", "evidence_verifications", ["chunk_id"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE evidence_verifications ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE evidence_verifications FORCE ROW LEVEL SECURITY")
        op.execute("""
            CREATE POLICY evidence_verifications_tenant_access
            ON evidence_verifications
            USING (tenant_id IN (
                SELECT tenant_id FROM tenant_memberships
                WHERE user_id = current_setting('app.user_id', true)
            ))
            WITH CHECK (tenant_id IN (
                SELECT tenant_id FROM tenant_memberships
                WHERE user_id = current_setting('app.user_id', true)
            ))
        """)
        op.execute("GRANT SELECT, INSERT ON TABLE evidence_verifications TO jurismind_app")

def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS evidence_verifications_tenant_access ON evidence_verifications")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE evidence_verifications FROM jurismind_app")
    op.drop_index("ix_evidence_verification_chunk", table_name="evidence_verifications")
    op.drop_index("ix_evidence_verification_tenant_created", table_name="evidence_verifications")
    op.drop_table("evidence_verifications")
