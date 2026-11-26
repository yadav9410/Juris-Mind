"""Mock-first Case Law Researcher specialist."""
from app.agents.base import MockSpecialistAgent


class CaseLawResearcher(MockSpecialistAgent):
    key = "case_law_researcher"
    display_name = "Case Law Researcher"
    description = "Review judgments, holdings, cited authorities and pinpoint references."
