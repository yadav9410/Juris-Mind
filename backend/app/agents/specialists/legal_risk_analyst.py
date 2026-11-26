"""Mock-first Legal Risk Analyst specialist."""
from app.agents.base import MockSpecialistAgent


class LegalRiskAnalyst(MockSpecialistAgent):
    key = "legal_risk_analyst"
    display_name = "Legal Risk Analyst"
    description = "Surface uncertainty, conflicting evidence, missing sources and legal risk questions."
