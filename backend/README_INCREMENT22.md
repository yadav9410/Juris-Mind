# JurisMind Increment 22 — Professional Platform

This is the final consolidated backend increment. It builds on the supplied Increment 21 project and adds matter management, task workflow, audit events, multi-agent research review using the existing supervisor, and a quality/completeness report.

## Included capabilities
- Tenant-scoped matter records.
- Matter tasks with workspace-member assignment, status, priority and due date.
- Audit events for matter/task/report/review creation and updates.
- Existing specialist-agent supervisor invoked in mock mode against an existing tenant research snapshot.
- Quality report that checks matter description, open tasks, linked drafts and human-review states.
- Tenant membership checks and PostgreSQL row-level security.
- Migration `0023_professional_platform`.

## Important boundaries
- Agent review uses the existing registered specialist agents and their mock execution mode through this endpoint. It does not invoke paid OpenAI execution. The existing agent workflow can be used separately where explicitly configured.
- Quality checks are completeness indicators, not legal correctness, citation authentication, source authenticity or professional approval.
- Audit events are application-level records; this is not a tamper-proof or externally immutable audit system.
- This increment does not add a frontend. The planned Streamlit frontend remains a later phase after backend completion.

## Installation — Windows PowerShell
1. Stop the API with `Ctrl+C`.
2. Back up the entire current Increment 21 project.
3. Extract this ZIP and merge its `app`, `migrations`, `tests` and `docs` folders into your existing project. Preserve `.env`, configuration and existing user data.
4. Activate your existing virtual environment.
5. From the project root run:

```powershell
python -m alembic upgrade head
python -m pytest -q tests/test_professional_platform_contract.py
python -m uvicorn app.main:app --reload
```

6. Open `http://127.0.0.1:8000/docs` and find `jurismind-professional-platform`.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/platform/matters` | Create matter |
| GET | `/platform/matters?tenant_id=...` | List matters |
| GET | `/platform/matters/{matter_id}` | Matter with tasks |
| PATCH | `/platform/matters/{matter_id}` | Update matter |
| POST | `/platform/matters/{matter_id}/tasks` | Create task |
| PATCH | `/platform/tasks/{task_id}` | Update task |
| GET | `/platform/matters/{matter_id}/audit` | View audit events |
| POST | `/platform/matters/{matter_id}/agent-review` | Run existing mock specialist review for a tenant research snapshot |
| POST | `/platform/matters/{matter_id}/quality-report` | Generate completeness/review checklist |
| GET | `/platform/matters/{matter_id}/reports` | List generated reports |

## Agent review request

```json
{
  "snapshot_id": "EXISTING_RESEARCH_SNAPSHOT_ID",
  "selected_agents": ["legislation_researcher", "case_law_researcher", "critic_reviewer"],
  "execution_mode": "mock"
}
```

The snapshot must belong to the same tenant as the matter. The agent supervisor returns its own limitations and requires human review.

## Verification
The ZIP is integrity-checked and all newly added Python files are syntax-compiled. Contract tests assert that routes and methods are exposed through OpenAPI. The migration has not been run against the user's PostgreSQL database; run it during installation and share the output if it fails.
