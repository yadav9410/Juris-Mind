"""Central allow-listed specialist registry."""
from app.agents.specialists.legislation_researcher import LegislationResearcher
from app.agents.specialists.case_law_researcher import CaseLawResearcher
from app.agents.specialists.jurisdiction_analyst import JurisdictionAnalyst
from app.agents.specialists.legal_risk_analyst import LegalRiskAnalyst
from app.agents.specialists.memo_writer import MemoWriter
from app.agents.specialists.critic_reviewer import CriticReviewer

AGENT_REGISTRY = {
    "legislation_researcher": LegislationResearcher,
    "case_law_researcher": CaseLawResearcher,
    "jurisdiction_analyst": JurisdictionAnalyst,
    "legal_risk_analyst": LegalRiskAnalyst,
    "memo_writer": MemoWriter,
    "critic_reviewer": CriticReviewer,
}


def get_agent(agent_key: str):
    """Instantiate only a registered specialist; never import arbitrary names."""
    try:
        return AGENT_REGISTRY[agent_key]()
    except KeyError as exc:
        raise ValueError(f"Unknown specialist agent: {agent_key}") from exc
