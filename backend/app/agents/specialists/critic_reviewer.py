"""Mock-first Critic / Quality Reviewer specialist."""
from app.agents.base import MockSpecialistAgent


class CriticReviewer(MockSpecialistAgent):
    key = "critic_reviewer"
    display_name = "Critic / Quality Reviewer"
    description = "Review completeness, traceability, contradictions and unsupported assertions."
