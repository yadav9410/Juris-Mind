"""Add PostgreSQL full-text GIN index for staged legal chunks.

Revision ID: 0007_full_text_search
Revises: 0006_ingestion_chunks
"""
from alembic import op

revision = "0007_full_text_search"
down_revision = "0006_ingestion_chunks"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite remains usable for local unit tests/development, but PostgreSQL is
    # required for the production full-text search endpoint and GIN index.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_ingestion_chunks_fts
            ON ingestion_chunks USING GIN (
                to_tsvector('simple', coalesce(heading, '') || ' ' || body_text)
            )
        """)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_ingestion_chunks_fts")
