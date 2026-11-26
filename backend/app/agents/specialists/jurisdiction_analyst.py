"""Mock-first Jurisdiction Analyst specialist."""
from app.agents.base import MockSpecialistAgent


class JurisdictionAnalyst(MockSpecialistAgent):
    key = "jurisdiction_analyst"
    display_name = "Jurisdiction Analyst"
    description = "Identify court hierarchy, territorial and subject-matter jurisdiction questions."
