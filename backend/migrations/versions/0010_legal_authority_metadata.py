"""Add candidate legal-authority metadata and source provenance to staged jobs.

Revision ID: 0010_legal_authority_metadata
Revises: 0009_search_runtime_read_access
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_legal_authority_metadata"
down_revision = "0009_search_runtime_read_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_jobs", sa.Column("metadata_json", sa.Text(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("metadata_review_status", sa.String(length=30), nullable=False, server_default="pending"))
    op.add_column("ingestion_jobs", sa.Column("source_name", sa.String(length=200), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("source_class", sa.String(length=30), nullable=False, server_default="unverified"))
    op.create_index("ix_ingestion_metadata_review", "ingestion_jobs", ["metadata_review_status", "created_at"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Runtime API remains read-only; ingest role already owns staged-job writes.
        op.execute("GRANT SELECT ON TABLE ingestion_jobs TO jurismind_app")


def downgrade() -> None:
    op.drop_index("ix_ingestion_metadata_review", table_name="ingestion_jobs")
    op.drop_column("ingestion_jobs", "source_class")
    op.drop_column("ingestion_jobs", "source_url")
    op.drop_column("ingestion_jobs", "source_name")
    op.drop_column("ingestion_jobs", "metadata_review_status")
    op.drop_column("ingestion_jobs", "metadata_json")
