"""Mock-first Legislation Researcher specialist."""
from app.agents.base import MockSpecialistAgent


class LegislationResearcher(MockSpecialistAgent):
    key = "legislation_researcher"
    display_name = "Legislation Researcher"
    description = "Identify relevant Acts, rules, provisions, commencement and amendment questions."
