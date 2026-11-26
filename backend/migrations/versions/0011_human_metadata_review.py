"""Human metadata review and authority verification workflow.

Revision ID: 0011_human_metadata_review
Revises: 0010_legal_authority_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_human_metadata_review"
down_revision = "0010_legal_authority_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_jobs", sa.Column("reviewed_metadata_json", sa.Text(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("authority_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("ingestion_jobs", sa.Column("authority_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("authority_verified_by", sa.String(length=100), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("authority_reference", sa.Text(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("authority_evidence", sa.Text(), nullable=True))
    op.create_table(
        "metadata_review_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("previous_metadata_json", sa.Text(), nullable=True),
        sa.Column("resulting_metadata_json", sa.Text(), nullable=True),
        sa.Column("authority_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_metadata_review_events_job_id", "metadata_review_events", ["job_id"])
    op.create_index("ix_metadata_review_job_created", "metadata_review_events", ["job_id", "created_at"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("GRANT SELECT, UPDATE (reviewed_metadata_json, metadata_review_status, authority_verified, authority_verified_at, authority_verified_by, authority_reference, authority_evidence) ON TABLE ingestion_jobs TO jurismind_app")
        op.execute("GRANT SELECT, INSERT ON TABLE metadata_review_events TO jurismind_app")


def downgrade() -> None:
    op.drop_index("ix_metadata_review_job_created", table_name="metadata_review_events")
    op.drop_index("ix_metadata_review_events_job_id", table_name="metadata_review_events")
    op.drop_table("metadata_review_events")
    for col in ("authority_evidence", "authority_reference", "authority_verified_by", "authority_verified_at", "authority_verified", "reviewed_metadata_json"):
        op.drop_column("ingestion_jobs", col)
