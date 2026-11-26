"""Add legal-aware staging chunks for ingested documents.

Revision ID: 0006_ingestion_chunks
Revises: 0005_ocr_classification
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_ingestion_chunks"
down_revision = "0005_ocr_classification"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ingestion_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(40), nullable=False),
        sa.Column("locator", sa.String(150)),
        sa.Column("heading", sa.String(500)),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
    )
    op.create_index("ix_ingestion_chunks_job_id", "ingestion_chunks", ["job_id"])
    op.create_index("ix_ingestion_chunk_job_ordinal", "ingestion_chunks", ["job_id", "ordinal"], unique=True)
    op.create_index("ix_ingestion_chunk_type_locator", "ingestion_chunks", ["chunk_type", "locator"])


def downgrade():
    op.drop_index("ix_ingestion_chunk_type_locator", table_name="ingestion_chunks")
    op.drop_index("ix_ingestion_chunk_job_ordinal", table_name="ingestion_chunks")
    op.drop_index("ix_ingestion_chunks_job_id", table_name="ingestion_chunks")
    op.drop_table("ingestion_chunks")
