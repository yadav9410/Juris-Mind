import json
import sys
import types
from types import SimpleNamespace

import pytest

from app.agents.contracts import AgentTask, EvidenceItem
from app.agents.openai_provider import (
    ProviderConfigurationError,
    ProviderResponseError,
    run_openai_agent,
)
from app.agents.registry import get_agent


def _task():
    return AgentTask(
        snapshot_id="snapshot-1",
        research_question="What statutory test applies?",
        sub_questions=["Identify the statutory test."],
        jurisdiction="India",
        court="Supreme Court of India",
        evidence=[
            EvidenceItem(
                evidence_id="ev-1",
                ordinal=1,
                sub_question="Identify the statutory test.",
                filename="Act.pdf",
                locator="Section 3",
                page_start=2,
                page_end=2,
                snippet="Illustrative source passage.",
            )
        ],
    )


def _fake_openai_module(content, usage=(100, 50, 150)):
    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    message=SimpleNamespace(content=content)
                )],
                usage=SimpleNamespace(
                    prompt_tokens=usage[0],
                    completion_tokens=usage[1],
                    total_tokens=usage[2],
                ),
            )

    class FakeClient:
        def __init__(self, **kwargs):
            calls["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(
                completions=FakeCompletions()
            )

    module = types.ModuleType("openai")
    module.OpenAI = FakeClient
    return module, calls


def test_openai_provider_validates_structured_output_and_usage(monkeypatch):
    content = json.dumps({
        "findings": [{
            "finding": "The supplied passage refers to Section 3.",
            "evidence_ids": ["ev-1"],
            "confidence": "medium",
            "caveats": ["The complete Act must be checked."],
        }],
        "questions_for_follow_up": ["Check commencement."],
    })
    fake, calls = _fake_openai_module(content)
    monkeypatch.setitem(sys.modules, "openai", fake)
    monkeypatch.setattr(
        "app.agents.openai_provider.get_settings",
        lambda: SimpleNamespace(
            openai_api_key="test-key",
            openai_model="test-model",
            openai_max_output_tokens=500,
            openai_timeout_seconds=10,
        ),
    )

    result = run_openai_agent(get_agent("legislation_researcher"), _task())

    assert result.execution_provider == "openai"
    assert result.findings[0].evidence_ids == ["ev-1"]
    assert result.usage["total_tokens"] == 150
    assert calls["model"] == "test-model"
    assert calls["response_format"] == {"type": "json_object"}


def test_openai_provider_rejects_invented_evidence_ids(monkeypatch):
    content = json.dumps({
        "findings": [{
            "finding": "Unsupported claim.",
            "evidence_ids": ["fabricated-id"],
            "confidence": "high",
            "caveats": [],
        }],
        "questions_for_follow_up": [],
    })
    fake, _ = _fake_openai_module(content)
    monkeypatch.setitem(sys.modules, "openai", fake)
    monkeypatch.setattr(
        "app.agents.openai_provider.get_settings",
        lambda: SimpleNamespace(
            openai_api_key="test-key",
            openai_model="test-model",
            openai_max_output_tokens=500,
            openai_timeout_seconds=10,
        ),
    )

    with pytest.raises(ProviderResponseError, match="evidence validation"):
        run_openai_agent(get_agent("case_law_researcher"), _task())


def test_openai_provider_requires_api_key(monkeypatch):
    monkeypatch.setattr(
        "app.agents.openai_provider.get_settings",
        lambda: SimpleNamespace(openai_api_key=None),
    )
    with pytest.raises(ProviderConfigurationError, match="OPENAI_API_KEY"):
        run_openai_agent(get_agent("memo_writer"), _task())
