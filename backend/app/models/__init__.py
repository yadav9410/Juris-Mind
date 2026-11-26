"""Import all models so SQLAlchemy and Alembic can discover their tables."""

from app.models.tenant import AppUser, Tenant, TenantMembership
from app.models.legal import (
    AuditEvent, DocumentEvent, DocumentVersion, JudgmentParagraph,
    LegalDocument, LegalProvision, LegalWork, SourceRecord,
)

__all__ = [
    "AppUser", "Tenant", "TenantMembership", "AuditEvent", "DocumentEvent",
    "DocumentVersion", "JudgmentParagraph", "LegalDocument",
    "LegalProvision", "LegalWork", "SourceRecord", "IngestionJob", "IngestionChunk", "MetadataReviewEvent", "CitationReference", "VerificationRecord", "ResearchSnapshot", "ResearchSnapshotEvidence", "ResearchAgentRun", "ResearchAgentOutput", "ResearchClaimAssessment", "EvidenceVerification", "AuthorityTreatment", "AuthorityTreatmentReview", "StatutoryInstrument", "StatutoryProvision", "StatutoryVersion", "StatutoryEvent", "JudgmentAnalysis", "LegalReasoningWorkspace", "LegalDraft", "PlatformMatter", "PlatformTask", "PlatformAuditEvent", "PlatformReport", "ResearchJob",
]

from app.models.ingestion import IngestionJob, IngestionChunk, MetadataReviewEvent

from app.models.citation import CitationReference, VerificationRecord

from app.models.research import ResearchSnapshot, ResearchSnapshotEvidence

from app.models.agent import ResearchAgentRun, ResearchAgentOutput

from app.models.claim import ResearchClaimAssessment
from app.models.evidence import EvidenceVerification

from app.models.authority import AuthorityTreatment, AuthorityTreatmentReview

from app.models.statutory import StatutoryInstrument, StatutoryProvision, StatutoryVersion, StatutoryEvent

from app.models.judgment import JudgmentAnalysis

from app.models.reasoning import LegalReasoningWorkspace

from app.models.due_diligence import DueDiligenceMatter, DueDiligenceRisk, DocumentComparison

from app.models.drafting import LegalDraft

from app.models.platform import PlatformMatter, PlatformTask, PlatformAuditEvent, PlatformReport

from app.models.research_job import ResearchJob
