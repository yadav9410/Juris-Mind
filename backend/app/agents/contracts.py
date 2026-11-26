"""Typed contracts shared by the supervisor and specialist agents."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    ordinal: int
    sub_question: str
    filename: str | None
    locator: str | None
    page_start: int | None
    page_end: int | None
    snippet: str
    chunk_id: str | None = None
    job_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentTask:
    snapshot_id: str
    research_question: str
    sub_questions: list[str]
    jurisdiction: str | None
    court: str | None
    evidence: list[EvidenceItem]
    evidence_limit: int = 40


@dataclass
class AgentFinding:
    finding: str
    evidence_ids: list[str] = field(default_factory=list)
    confidence: str = "limited"
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentResult:
    agent_key: str
    display_name: str
    status: str
    findings: list[AgentFinding]
    questions_for_follow_up: list[str] = field(default_factory=list)
    execution_provider: str = "mock"
    error: str | None = None
    usage: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_key": self.agent_key,
            "display_name": self.display_name,
            "status": self.status,
            "findings": [item.to_dict() for item in self.findings],
            "questions_for_follow_up": self.questions_for_follow_up,
            "execution_provider": self.execution_provider,
            "error": self.error,
            "usage": self.usage,
        }
