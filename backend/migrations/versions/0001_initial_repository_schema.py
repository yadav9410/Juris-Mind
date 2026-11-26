"""Create JurisMind's initial legal repository schema.

Revision ID: 0001_initial
Revises: none
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Workspace and user tables from Increment 1.
    op.create_table("tenants", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("app_users", sa.Column("id", sa.String(100), primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("tenant_memberships", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.String(100), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"))

    # Shared public legal corpus: a legal work can have several source documents.
    op.create_table("legal_works", sa.Column("id", sa.String(36), primary_key=True), sa.Column("work_type", sa.String(40), nullable=False), sa.Column("title", sa.String(500), nullable=False), sa.Column("canonical_identifier", sa.String(250)), sa.Column("jurisdiction", sa.String(100), nullable=False), sa.Column("court_name", sa.String(200)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("work_type", "canonical_identifier", name="uq_legal_work_identifier"))
    op.create_index("ix_legal_work_type_jurisdiction", "legal_works", ["work_type", "jurisdiction"])
    op.create_table("source_records", sa.Column("id", sa.String(36), primary_key=True), sa.Column("source_name", sa.String(200), nullable=False), sa.Column("source_url", sa.Text), sa.Column("source_class", sa.String(30), nullable=False), sa.Column("terms_review_status", sa.String(30), nullable=False), sa.Column("notes", sa.Text), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_source_classification", "source_records", ["source_class", "source_name"])
    op.create_table("legal_documents", sa.Column("id", sa.String(36), primary_key=True), sa.Column("legal_work_id", sa.String(36), sa.ForeignKey("legal_works.id", ondelete="RESTRICT"), nullable=False), sa.Column("source_id", sa.String(36), sa.ForeignKey("source_records.id", ondelete="RESTRICT"), nullable=False), sa.Column("document_kind", sa.String(40), nullable=False), sa.Column("canonical_url", sa.Text), sa.Column("language", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_legal_document_work", "legal_documents", ["legal_work_id"])
    op.create_index("ix_legal_document_source", "legal_documents", ["source_id"])

    # Immutable captured file/text versions and their temporal metadata.
    op.create_table("document_versions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_id", sa.String(36), sa.ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=False), sa.Column("version_label", sa.String(100)), sa.Column("content_sha256", sa.String(64), nullable=False), sa.Column("storage_key", sa.Text), sa.Column("extracted_text_key", sa.Text), sa.Column("publication_date", sa.DateTime(timezone=True)), sa.Column("valid_from", sa.DateTime(timezone=True)), sa.Column("valid_to", sa.DateTime(timezone=True)), sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False), sa.Column("extraction_status", sa.String(30), nullable=False), sa.Column("verification_status", sa.String(30), nullable=False), sa.Column("page_count", sa.Integer), sa.UniqueConstraint("document_id", "content_sha256", name="uq_document_version_hash"))
    op.create_index("ix_document_version_capture", "document_versions", ["document_id", "captured_at"])
    op.create_table("legal_provisions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False), sa.Column("provision_ref", sa.String(100), nullable=False), sa.Column("heading", sa.String(500)), sa.Column("body_text", sa.Text, nullable=False), sa.Column("page_start", sa.Integer), sa.Column("page_end", sa.Integer), sa.UniqueConstraint("document_version_id", "provision_ref", name="uq_version_provision_ref"))
    op.create_index("ix_provision_ref", "legal_provisions", ["provision_ref"])
    op.create_table("judgment_paragraphs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False), sa.Column("paragraph_number", sa.String(30), nullable=False), sa.Column("body_text", sa.Text, nullable=False), sa.Column("page_number", sa.Integer), sa.UniqueConstraint("document_version_id", "paragraph_number", name="uq_version_paragraph_number"))
    op.create_index("ix_judgment_paragraph_number", "judgment_paragraphs", ["paragraph_number"])

    # Legal events and audit history are append-only records at application level.
    op.create_table("document_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("legal_work_id", sa.String(36), sa.ForeignKey("legal_works.id", ondelete="CASCADE"), nullable=False), sa.Column("event_type", sa.String(40), nullable=False), sa.Column("event_date", sa.DateTime(timezone=True)), sa.Column("description", sa.Text), sa.Column("evidence_version_id", sa.String(36), sa.ForeignKey("document_versions.id", ondelete="SET NULL")), sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_document_event_work_date", "document_events", ["legal_work_id", "event_date"])
    op.create_table("audit_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="SET NULL")), sa.Column("actor_user_id", sa.String(100), sa.ForeignKey("app_users.id", ondelete="SET NULL")), sa.Column("action", sa.String(100), nullable=False), sa.Column("resource_type", sa.String(100), nullable=False), sa.Column("resource_id", sa.String(100)), sa.Column("outcome", sa.String(30), nullable=False), sa.Column("details_json", sa.Text), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_tenant_created", "audit_events", ["tenant_id", "created_at"])

def downgrade():
    # Drop dependent tables first so foreign-key relationships remain valid.
    for table in ["audit_events", "document_events", "judgment_paragraphs", "legal_provisions", "document_versions", "legal_documents", "source_records", "legal_works", "tenant_memberships", "app_users", "tenants"]:
        op.drop_table(table)
