"""Add evidence-linked judicial authority treatment records.

Revision ID: 0017_authority_treatment
Revises: 0016_evidence_integrity
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_authority_treatment"
down_revision = "0016_evidence_integrity"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "authority_treatments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subject_citation", sa.String(300), nullable=False),
        sa.Column("subject_title", sa.String(500)),
        sa.Column("subject_job_id", sa.String(36), sa.ForeignKey("ingestion_jobs.id", ondelete="SET NULL")),
        sa.Column("treatment_type", sa.String(40), nullable=False),
        sa.Column("treatment_scope", sa.Text(), nullable=False),
        sa.Column("treating_job_id", sa.String(36), sa.ForeignKey("ingestion_jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_chunk_id", sa.String(36), sa.ForeignKey("ingestion_chunks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_verification_id", sa.String(36), sa.ForeignKey("evidence_verifications.id", ondelete="SET NULL")),
        sa.Column("treating_decision_date", sa.Date()),
        sa.Column("treatment_review_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("source_integrity_status", sa.String(30), nullable=False, server_default="not_checked"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_authority_treatment_tenant_created", "authority_treatments", ["tenant_id", "created_at"])
    op.create_index("ix_authority_treatment_subject_citation", "authority_treatments", ["subject_citation"])
    op.create_index("ix_authority_treatment_treating_job", "authority_treatments", ["treating_job_id"])

    op.create_table(
        "authority_treatment_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("treatment_id", sa.String(36), sa.ForeignKey("authority_treatments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_user_id", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_authority_treatment_review_record", "authority_treatment_reviews", ["treatment_id", "created_at"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("authority_treatments", "authority_treatment_reviews"):
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
        op.execute("GRANT SELECT, INSERT ON TABLE authority_treatments TO jurismind_app")
        op.execute("GRANT SELECT, INSERT ON TABLE authority_treatment_reviews TO jurismind_app")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS authority_treatment_reviews_tenant_access ON authority_treatment_reviews")
        op.execute("DROP POLICY IF EXISTS authority_treatments_tenant_access ON authority_treatments")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE authority_treatment_reviews FROM jurismind_app")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE authority_treatments FROM jurismind_app")
    op.drop_index("ix_authority_treatment_review_record", table_name="authority_treatment_reviews")
    op.drop_table("authority_treatment_reviews")
    op.drop_index("ix_authority_treatment_treating_job", table_name="authority_treatments")
    op.drop_index("ix_authority_treatment_subject_citation", table_name="authority_treatments")
    op.drop_index("ix_authority_treatment_tenant_created", table_name="authority_treatments")
    op.drop_table("authority_treatments")
