"""Add OCR and classification metadata to ingestion jobs.

Revision ID: 0005_ocr_classification
Revises: 0004_ingestion_jobs
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_ocr_classification"
down_revision = "0004_ingestion_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ingestion_jobs", sa.Column("ocr_used", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("ingestion_jobs", sa.Column("classification_json", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("ingestion_jobs", "classification_json")
    op.drop_column("ingestion_jobs", "ocr_used")
