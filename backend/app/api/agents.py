
"""Authenticated API for specialist-agent supervisor runs."""

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.registry import AGENT_REGISTRY
from app.agents.supervisor import run_supervisor
from app.core.config import get_settings
from app.db.session import get_db
from app.models.agent import ResearchAgentRun, ResearchAgentOutput
from app.models.research import ResearchSnapshot
from app.models.tenant import TenantMembership
from app.security.auth import get_current_user


router = APIRouter(prefix="/research", tags=["specialist-agents"])


class AgentExecutionRequest(BaseModel):
    """Request to execute selected specialist agents."""

    tenant_id: str = Field(min_length=1, max_length=36)
    agent_keys: list[str] | None = Field(default=None, max_length=6)
    execution_mode: str = Field(
        default="mock",
        pattern="^(mock|openai)$",
    )


def _require_membership(
    db: Session,
    tenant_id: str,
    user_id: str,
):
    """Return the user's membership in the requested workspace."""

    return db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
        ).limit(1)
    )


@router.post(
    "/snapshots/{snapshot_id}/agents/execute",
    status_code=201,
)
def execute_specialist_agents(
    snapshot_id: str,
    payload: AgentExecutionRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user),
):
    """Run selected specialists in mock or explicitly enabled OpenAI mode."""

    user_id = claims.get("app_user_id")

    if not user_id:
        raise HTTPException(
            status_code=403,
            detail="Workspace identity is unavailable.",
        )

    # Verify workspace membership.
    membership = _require_membership(
        db,
        payload.tenant_id,
        user_id,
    )

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="Workspace membership is required.",
        )

    if membership.role == "viewer":
        raise HTTPException(
            status_code=403,
            detail="Viewer role cannot execute research agents.",
        )

    # Verify that the snapshot belongs to the requested workspace.
    snapshot = db.scalar(
        select(ResearchSnapshot).where(
            ResearchSnapshot.id == snapshot_id,
            ResearchSnapshot.tenant_id == payload.tenant_id,
        )
    )

    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail="Research snapshot not found.",
        )

    # Check provider configuration when OpenAI mode is requested.
    settings = get_settings()

    if payload.execution_mode == "openai":
        if not settings.openai_enabled:
            raise HTTPException(
                status_code=403,
                detail=(
                    "OpenAI execution is disabled. "
                    "Set OPENAI_ENABLED=true and restart the API."
                ),
            )

        if not settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is not configured on the API server.",
            )

    try:
        run = run_supervisor(
            db,
            snapshot=snapshot,
            user_id=user_id,
            selected_agents=payload.agent_keys,
            execution_mode=payload.execution_mode,
        )

        # Capture the response before committing the transaction.
        response_data = {
            "run_id": run.id,
            "snapshot_id": run.snapshot_id,
            "tenant_id": run.tenant_id,
            "execution_mode": run.execution_mode,
            "status": run.status,
            "summary": json.loads(run.supervisor_summary),
            "limitations": run.limitations,
        }

        db.commit()

        return response_data

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise


@router.get("/agent-runs/{run_id}")
def get_agent_run(
    run_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user),
):
    """Read one supervisor run and its persisted specialist outputs."""

    user_id = claims.get("app_user_id")

    if not user_id:
        raise HTTPException(
            status_code=403,
            detail="Workspace identity is unavailable.",
        )

    # Step 1: Find the authenticated user's workspace memberships.
    memberships = db.scalars(
        select(TenantMembership).where(
            TenantMembership.user_id == user_id,
        )
    ).all()

    if not memberships:
        raise HTTPException(
            status_code=404,
            detail="Agent run not found.",
        )

    # Step 2: Find the run only within one of those workspaces.
    tenant_ids = [membership.tenant_id for membership in memberships]

    run = db.scalar(
        select(ResearchAgentRun).where(
            ResearchAgentRun.id == run_id,
            ResearchAgentRun.tenant_id.in_(tenant_ids),
        )
    )

    if not run:
        raise HTTPException(
            status_code=404,
            detail="Agent run not found.",
        )

    # Step 3: Retrieve specialist outputs belonging to this run
    # and the same tenant.
    outputs = db.scalars(
        select(ResearchAgentOutput)
        .where(
            ResearchAgentOutput.run_id == run.id,
            ResearchAgentOutput.tenant_id == run.tenant_id,
        )
        .order_by(ResearchAgentOutput.ordinal.asc())
    ).all()

    # Step 4: Build the response.
    return {
        "run_id": run.id,
        "snapshot_id": run.snapshot_id,
        "tenant_id": run.tenant_id,
        "execution_mode": run.execution_mode,
        "status": run.status,
        "summary": json.loads(run.supervisor_summary),
        "limitations": run.limitations,
        "outputs": [
            json.loads(row.output_json)
            for row in outputs
        ],
    }


@router.get("/agents")
def list_specialist_agents():
    """List available specialists without requiring a provider connection."""

    settings = get_settings()

    return {
        "default_execution_mode": "mock",
        "openai_execution_enabled": bool(
            settings.openai_enabled and settings.openai_api_key
        ),
        "agents": [
            {
                "agent_key": key,
                "display_name": agent().display_name,
                "description": agent().description,
            }
            for key, agent in AGENT_REGISTRY.items()
        ],
        "notice": (
            "Mock is the default. OpenAI mode requires "
            "OPENAI_ENABLED=true and OPENAI_API_KEY."
        ),
        "configured_model": (
            settings.openai_model
            if settings.openai_enabled
            else None
        ),
    }
