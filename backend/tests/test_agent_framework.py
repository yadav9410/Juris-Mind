import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401
from app.agents.registry import AGENT_REGISTRY, get_agent
from app.agents.supervisor import run_mock_supervisor
from app.models.tenant import Tenant, AppUser
from app.models.research import ResearchSnapshot, ResearchSnapshotEvidence
from app.models.agent import ResearchAgentRun, ResearchAgentOutput


def _database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _seed(db, *, with_evidence=True):
    db.add_all([
        Tenant(id="tenant-1", name="Test workspace"),
        AppUser(id="user-1", email="agent-test@example.com"),
    ])
    db.flush()
    snapshot = ResearchSnapshot(
        id="snapshot-1",
        tenant_id="tenant-1",
        created_by="user-1",
        question="What is the legal test for bail?",
        jurisdiction="India",
        court="Supreme Court of India",
        status="completed",
        plan_json=json.dumps({"sub_questions": ["Bail statutory test"]}),
        summary_json=json.dumps({"result_count": 1 if with_evidence else 0}),
        limitations="Research leads only.",
    )
    db.add(snapshot)
    db.flush()
    if with_evidence:
        db.add(ResearchSnapshotEvidence(
            id="evidence-1",
            snapshot_id=snapshot.id,
            tenant_id="tenant-1",
            ordinal=1,
            sub_question="Bail statutory test",
            chunk_id="chunk-1",
            job_id="job-1",
            filename="bail-judgment.pdf",
            locator="Paragraph 12",
            page_start=4,
            page_end=4,
            evidence_json=json.dumps({"snippet": "A mock evidence passage."}),
        ))
        db.flush()
    return snapshot


def test_registry_contains_all_six_specialists():
    assert len(AGENT_REGISTRY) == 6
    assert set(AGENT_REGISTRY) == {
        "legislation_researcher",
        "case_law_researcher",
        "jurisdiction_analyst",
        "legal_risk_analyst",
        "memo_writer",
        "critic_reviewer",
    }
    assert all(get_agent(key).key == key for key in AGENT_REGISTRY)


def test_supervisor_runs_six_mock_agents_and_persists_traceable_outputs():
    engine = _database()
    with Session(engine) as db:
        snapshot = _seed(db)
        run = run_mock_supervisor(db, snapshot=snapshot, user_id="user-1")
        db.commit()

        saved_run = db.get(ResearchAgentRun, run.id)
        outputs = db.scalars(
            select(ResearchAgentOutput)
            .where(ResearchAgentOutput.run_id == run.id)
            .order_by(ResearchAgentOutput.ordinal)
        ).all()

        assert saved_run.execution_mode == "mock"
        assert saved_run.status == "completed"
        summary = json.loads(saved_run.supervisor_summary)
        assert summary["evidence_count"] == 1
        assert summary["evidence_ready"] is True
        assert len(outputs) == 6
        assert [row.agent_key for row in outputs] == list(AGENT_REGISTRY)
        for row in outputs:
            payload = json.loads(row.output_json)
            assert payload["execution_provider"] == "mock"
            assert payload["findings"][0]["evidence_ids"] == ["evidence-1"]
            assert payload["findings"][0]["confidence"] == "limited"
        assert "not legal advice" in saved_run.limitations

    engine.dispose()


def test_supervisor_handles_snapshot_without_evidence_without_fabricating_sources():
    engine = _database()
    with Session(engine) as db:
        snapshot = _seed(db, with_evidence=False)
        run = run_mock_supervisor(
            db, snapshot=snapshot, user_id="user-1",
            selected_agents=["case_law_researcher"],
        )
        db.commit()
        output = db.scalars(
            select(ResearchAgentOutput).where(ResearchAgentOutput.run_id == run.id)
        ).one()
        payload = json.loads(output.output_json)
        assert run.status == "completed"
        summary = json.loads(run.supervisor_summary)
        assert summary["evidence_count"] == 0
        assert summary["evidence_ready"] is False
        assert summary["evidence_state"] == "no_evidence"
        assert payload["status"] == "no_evidence"
        assert payload["findings"][0]["evidence_ids"] == []
        assert payload["findings"][0]["confidence"] == "none"
    engine.dispose()


def test_supervisor_rejects_unknown_and_duplicate_agent_keys():
    engine = _database()
    with Session(engine) as db:
        snapshot = _seed(db)
        with pytest.raises(ValueError, match="Unknown specialist"):
            run_mock_supervisor(
                db, snapshot=snapshot, user_id="user-1",
                selected_agents=["unregistered_agent"],
            )
        with pytest.raises(ValueError, match="Duplicate"):
            run_mock_supervisor(
                db, snapshot=snapshot, user_id="user-1",
                selected_agents=["memo_writer", "memo_writer"],
            )
    engine.dispose()


def test_specialist_outputs_explicitly_remain_mock_provider():
    task_agent = get_agent("legal_risk_analyst")
    from app.agents.contracts import AgentTask
    result = task_agent.run(AgentTask(
        snapshot_id="s1",
        research_question="Question",
        sub_questions=["Risk?"],
        jurisdiction=None,
        court=None,
        evidence=[],
    ))
    assert result.execution_provider == "mock"
    assert result.status == "no_evidence"
    assert result.findings[0].confidence == "none"
