"""Deterministic supervisor that runs the six mock specialists in sequence."""
from __future__ import annotations

import json
from sqlalchemy.orm import Session

from app.agents.contracts import AgentTask, EvidenceItem
from app.agents.registry import AGENT_REGISTRY, get_agent
from app.models.agent import ResearchAgentRun, ResearchAgentOutput
from app.models.research import ResearchSnapshot, ResearchSnapshotEvidence

SUPERVISOR_LIMITATIONS = (
    "Agent outputs are research assistance, not legal advice or final legal "
    "conclusions. Agents do not independently certify citations, determine current "
    "law, or prove proposition-to-source support. Citation verification remains "
    "the deterministic Increment 9 service. Human review is required."
)


def _evidence_item(row: ResearchSnapshotEvidence) -> EvidenceItem:
    try:
        data = json.loads(row.evidence_json)
    except (TypeError, json.JSONDecodeError):
        data = {}
    snippet = str(data.get("snippet") or data.get("body_text") or "")[:3000]
    return EvidenceItem(
        evidence_id=row.id,
        ordinal=row.ordinal,
        sub_question=row.sub_question,
        filename=row.filename,
        locator=row.locator,
        page_start=row.page_start,
        page_end=row.page_end,
        snippet=snippet,
        chunk_id=row.chunk_id,
        job_id=row.job_id,
    )


def run_supervisor(
    db: Session,
    *,
    snapshot: ResearchSnapshot,
    user_id: str,
    selected_agents: list[str] | None = None,
    execution_mode: str = "mock",
) -> ResearchAgentRun:
    """Run registered specialists in mock or explicitly enabled OpenAI mode."""
    if execution_mode not in {"mock", "openai"}:
        raise ValueError("execution_mode must be 'mock' or 'openai'.")
    keys = selected_agents or list(AGENT_REGISTRY.keys())
    if not keys:
        raise ValueError("At least one specialist agent must be selected.")
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate specialist agent keys are not allowed.")
    unknown = [key for key in keys if key not in AGENT_REGISTRY]
    if unknown:
        raise ValueError(f"Unknown specialist agent(s): {', '.join(unknown)}")

    try:
        plan = json.loads(snapshot.plan_json)
    except (TypeError, json.JSONDecodeError):
        plan = {"sub_questions": []}

    rows = db.query(ResearchSnapshotEvidence).filter(
        ResearchSnapshotEvidence.snapshot_id == snapshot.id,
        ResearchSnapshotEvidence.tenant_id == snapshot.tenant_id,
    ).order_by(ResearchSnapshotEvidence.ordinal.asc()).limit(40).all()

    task = AgentTask(
        snapshot_id=snapshot.id,
        research_question=snapshot.question,
        sub_questions=plan.get("sub_questions", []),
        jurisdiction=snapshot.jurisdiction,
        court=snapshot.court,
        evidence=[_evidence_item(row) for row in rows],
    )

    run = ResearchAgentRun(
        tenant_id=snapshot.tenant_id,
        snapshot_id=snapshot.id,
        initiated_by=user_id,
        execution_mode=execution_mode,
        status="running",
        supervisor_summary=f"Supervisor started {execution_mode} execution.",
        limitations=SUPERVISOR_LIMITATIONS,
    )
    db.add(run)
    db.flush()

    results = []
    for ordinal, key in enumerate(keys, start=1):
        try:
            agent = get_agent(key)
            if execution_mode == "openai":
                from app.agents.openai_provider import run_openai_agent
                result = run_openai_agent(agent, task)
            else:
                result = agent.run(task)
            results.append(result)
            status = result.status
            payload = result.to_dict()
        except Exception as exc:  # isolate one specialist failure from others
            status = "failed"
            payload = {
                "agent_key": key,
                "display_name": key,
                "status": "failed",
                "findings": [],
                "questions_for_follow_up": [],
                 "execution_provider": execution_mode,
                "error": f"{type(exc).__name__}: specialist execution failed",
                "usage": {},
            }
        db.add(ResearchAgentOutput(
            run_id=run.id,
            tenant_id=snapshot.tenant_id,
            agent_key=key,
            display_name=payload["display_name"],
            ordinal=ordinal,
            status=status,
            output_json=json.dumps(payload, ensure_ascii=False),
        ))

    completed = sum(1 for item in results if item.status in {"completed", "no_evidence"})
    failed = len(keys) - completed
    run.status = "completed" if failed == 0 else ("partial" if completed else "failed")
    usage_totals = {
        "input_tokens": sum(item.usage.get("input_tokens", 0) for item in results),
        "output_tokens": sum(item.usage.get("output_tokens", 0) for item in results),
        "total_tokens": sum(item.usage.get("total_tokens", 0) for item in results),
    }
    run.supervisor_summary = json.dumps({
        "agent_count": len(keys),
        "completed_count": completed,
        "failed_count": failed,
        "execution_mode": execution_mode,
        "evidence_count": len(task.evidence),
        "evidence_ready": bool(task.evidence),
        "evidence_state": "available" if task.evidence else "no_evidence",
        "token_usage": usage_totals,
        "agents": [item.to_dict() for item in results],
    }, ensure_ascii=False)
    db.flush()
    return run


def run_mock_supervisor(
    db: Session,
    *,
    snapshot: ResearchSnapshot,
    user_id: str,
    selected_agents: list[str] | None = None,
) -> ResearchAgentRun:
    """Backward-compatible wrapper for the Increment 11 mock test suite."""
    return run_supervisor(
        db,
        snapshot=snapshot,
        user_id=user_id,
        selected_agents=selected_agents,
        execution_mode="mock",
    )
