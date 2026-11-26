"""Grant the restricted API role read access to shared staged-search tables.

Revision ID: 0009_search_runtime_read_access
Revises: 0008_identity_tenant_isolation
"""
from alembic import op

revision = "0009_search_runtime_read_access"
down_revision = "0008_identity_tenant_isolation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # These staging records represent the shared public legal corpus.
    # The API role can search them but cannot create, modify, or delete them.
    op.execute("GRANT SELECT ON TABLE ingestion_jobs, ingestion_chunks TO jurismind_app")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("REVOKE SELECT ON TABLE ingestion_jobs, ingestion_chunks FROM jurismind_app")
