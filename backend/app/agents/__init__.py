"""JurisMind specialist-agent framework.

The default provider is mock-only. Real LLM execution is intentionally not
wired in this increment and must be enabled in a separately approved stage.
"""
from app.agents.registry import AGENT_REGISTRY, get_agent

__all__ = ["AGENT_REGISTRY", "get_agent"]
