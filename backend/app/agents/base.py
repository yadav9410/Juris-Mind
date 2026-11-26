"""Base interface and evidence-safe mock implementation for specialists."""
from __future__ import annotations

from abc import ABC, abstractmethod
from app.agents.contracts import AgentFinding, AgentResult, AgentTask


class SpecialistAgent(ABC):
    key: str
    display_name: str
    description: str

    @abstractmethod
    def run(self, task: AgentTask) -> AgentResult:
        """Execute a bounded task and return structured, traceable findings."""


class MockSpecialistAgent(SpecialistAgent):
    """Deterministic mock agent used for framework testing without API costs."""

    key = "base"
    display_name = "Base Specialist"
    description = "Base mock specialist"

    def run(self, task: AgentTask) -> AgentResult:
        related = task.evidence[:task.evidence_limit]
        if related:
            finding = AgentFinding(
                finding=(
                    f"{self.display_name} mock review inspected {len(related)} "
                    "retrieved evidence item(s). No substantive legal conclusion "
                    "is asserted by this mock implementation."
                ),
                evidence_ids=[item.evidence_id for item in related],
                confidence="limited",
                caveats=[
                    "Mock output only; replace with a reviewed specialist prompt and provider.",
                    "Retrieved evidence is not proof that a legal proposition is correct.",
                    "Verify the original source, applicable version and authority status.",
                ],
            )
            status = "completed"
        else:
            finding = AgentFinding(
                finding=(
                    f"{self.display_name} received no retrieved evidence. "
                    "No substantive legal conclusion can be made."
                ),
                evidence_ids=[],
                confidence="none",
                caveats=["No evidence was supplied to this agent.", "Mock output only."],
            )
            status = "no_evidence"
        return AgentResult(
            agent_key=self.key,
            display_name=self.display_name,
            status=status,
            findings=[finding],
            questions_for_follow_up=[
                "Which primary legal sources or additional documents should be indexed?"
            ] if not related else [],
        )
