"""Add ingestion job tracking.

Revision ID: 0004_ingestion_jobs
Revises: 0003_role_audit_rls
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_ingestion_jobs"
down_revision = "0003_role_audit_rls"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("storage_key", sa.Text()),
        sa.Column("extracted_text_key", sa.Text()),
        sa.Column("page_count", sa.Integer()),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ingestion_jobs_content_sha256", "ingestion_jobs", ["content_sha256"])
    op.create_index("ix_ingestion_status_created", "ingestion_jobs", ["status", "created_at"])

def downgrade():
    op.drop_table("ingestion_jobs")
