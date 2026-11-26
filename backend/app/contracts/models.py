from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from .enums import LegalDomain, SourceTier, SourceType, TaskStatus, VerificationStatus


class Jurisdiction(BaseModel):
    country_code: str = Field(default="IN", min_length=2, max_length=2)
    state_code: str | None = Field(default="UP", description="ISO-like internal code; UP means Uttar Pradesh.")
    state_name: str | None = "Uttar Pradesh"
    court_name: str | None = None
    territorial_notes: str | None = None


class LegalResearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=10, max_length=12000)
    facts: str | None = Field(default=None, max_length=30000)
    requested_domains: list[LegalDomain] = Field(default_factory=list)
    jurisdiction: Jurisdiction = Field(default_factory=Jurisdiction)
    as_of_date: date = Field(default_factory=date.today)
    clarification_allowed: bool = True
    uploaded_file_ids: list[str] = Field(default_factory=list)
    output_formats: list[str] = Field(default_factory=lambda: ["pdf", "docx"])


class ResearchTask(BaseModel):
    task_id: str
    agent_name: str
    objective: str
    domain: LegalDomain | None = None
    jurisdiction: Jurisdiction
    required_source_types: list[SourceType] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    depends_on: list[str] = Field(default_factory=list)


class SourceReference(BaseModel):
    source_id: str
    title: str
    source_type: SourceType
    source_tier: SourceTier
    url: HttpUrl | None = None
    publisher: str | None = None
    jurisdiction: Jurisdiction | None = None
    published_date: date | None = None
    effective_from: date | None = None
    retrieved_at: datetime | None = None
    document_version: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    paragraph_number: str | None = None
    section_number: str | None = None
    excerpt: str | None = None
    checksum_sha256: str | None = None


class CitationCheck(BaseModel):
    citation_id: str
    claim_id: str
    source_id: str | None = None
    identity_status: VerificationStatus = VerificationStatus.UNVERIFIED
    pinpoint_status: VerificationStatus = VerificationStatus.UNVERIFIED
    support_status: VerificationStatus = VerificationStatus.UNVERIFIED
    notes: list[str] = Field(default_factory=list)


class LegalClaim(BaseModel):
    claim_id: str
    text: str
    materiality: str = "material"
    source_ids: list[str] = Field(default_factory=list)
    caveat: str | None = None


class MemoSection(BaseModel):
    heading: str
    content: str
    claim_ids: list[str] = Field(default_factory=list)


class LegalMemo(BaseModel):
    memo_id: str
    research_run_id: str
    title: str
    jurisdiction: Jurisdiction
    as_of_date: date
    status: str = "draft_for_lawyer_review"
    executive_summary: str
    assumptions: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    sections: list[MemoSection] = Field(default_factory=list)
    claims: list[LegalClaim] = Field(default_factory=list)
    citations: list[CitationCheck] = Field(default_factory=list)
    source_registry: list[SourceReference] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    agent_name: str
    research_run_id: str
    summary: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
