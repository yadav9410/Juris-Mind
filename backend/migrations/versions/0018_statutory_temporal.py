"""Create shared statutory temporal-version records.

Revision ID: 0018_statutory_temporal
Revises: 0017_authority_treatment
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_statutory_temporal"
down_revision = "0017_authority_treatment"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "statutory_instruments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("canonical_identifier", sa.String(250), nullable=False, unique=True),
        sa.Column("instrument_type", sa.String(40), nullable=False),
        sa.Column("jurisdiction", sa.String(150), nullable=False, server_default="India"),
        sa.Column("enactment_date", sa.Date()),
        sa.Column("publication_date", sa.Date()),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_statutory_instrument_title", "statutory_instruments", ["title"])

    op.create_table(
        "statutory_provisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instrument_id", sa.String(36), sa.ForeignKey("statutory_instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provision_ref", sa.String(120), nullable=False),
        sa.Column("heading", sa.String(500)),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("instrument_id", "provision_ref", name="uq_statutory_provision_ref"),
    )
    op.create_index("ix_statutory_provision_ref", "statutory_provisions", ["provision_ref"])

    op.create_table(
        "statutory_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provision_id", sa.String(36), sa.ForeignKey("statutory_provisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_label", sa.String(120)),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()),
        sa.Column("commencement_date", sa.Date()),
        sa.Column("publication_date", sa.Date()),
        sa.Column("source_job_id", sa.String(36), sa.ForeignKey("ingestion_jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_chunk_id", sa.String(36), sa.ForeignKey("ingestion_chunks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_verification_id", sa.String(36), sa.ForeignKey("evidence_verifications.id", ondelete="SET NULL")),
        sa.Column("verification_status", sa.String(30), nullable=False, server_default="unverified"),
        sa.Column("closed_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT")),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_statutory_version_provision_dates", "statutory_versions", ["provision_id", "effective_from", "effective_to"])
    op.create_index("ix_statutory_version_source_chunk", "statutory_versions", ["source_chunk_id"])

    op.create_table(
        "statutory_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provision_id", sa.String(36), sa.ForeignKey("statutory_provisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amending_instrument", sa.String(500)),
        sa.Column("source_job_id", sa.String(36), sa.ForeignKey("ingestion_jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_chunk_id", sa.String(36), sa.ForeignKey("ingestion_chunks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_verification_id", sa.String(36), sa.ForeignKey("evidence_verifications.id", ondelete="SET NULL")),
        sa.Column("created_by", sa.String(100), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_statutory_event_provision_date", "statutory_events", ["provision_id", "event_date"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Shared corpus: every provisioned workspace member may read; only owners/admins may write.
        for table in ("statutory_instruments", "statutory_provisions", "statutory_versions", "statutory_events"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(f"""
                CREATE POLICY {table}_member_read ON {table}
                FOR SELECT USING (EXISTS (
                    SELECT 1 FROM tenant_memberships tm
                    WHERE tm.user_id = current_setting('app.user_id', true)
                ))
            """)
            op.execute(f"""
                CREATE POLICY {table}_admin_write ON {table}
                FOR INSERT WITH CHECK (EXISTS (
                    SELECT 1 FROM tenant_memberships tm
                    WHERE tm.user_id = current_setting('app.user_id', true)
                    AND tm.role IN ('owner', 'admin')
                ))
            """)
        op.execute("GRANT SELECT, INSERT ON TABLE statutory_instruments, statutory_provisions, statutory_versions, statutory_events TO jurismind_app")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("statutory_events", "statutory_versions", "statutory_provisions", "statutory_instruments"):
            op.execute(f"DROP POLICY IF EXISTS {table}_member_read ON {table}")
            op.execute(f"DROP POLICY IF EXISTS {table}_admin_write ON {table}")
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM jurismind_app")
    op.drop_index("ix_statutory_event_provision_date", table_name="statutory_events")
    op.drop_table("statutory_events")
    op.drop_index("ix_statutory_version_source_chunk", table_name="statutory_versions")
    op.drop_index("ix_statutory_version_provision_dates", table_name="statutory_versions")
    op.drop_table("statutory_versions")
    op.drop_index("ix_statutory_provision_ref", table_name="statutory_provisions")
    op.drop_table("statutory_provisions")
    op.drop_index("ix_statutory_instrument_title", table_name="statutory_instruments")
    op.drop_table("statutory_instruments")
