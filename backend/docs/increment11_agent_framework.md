# JurisMind Increment 11 — Specialist Agent Framework (Mock-First)

## Goal

Establish the complete specialist-agent framework and validate its coordination, structured outputs, evidence traceability, persistence and API surface using deterministic mock implementations. Real LLM execution is intentionally disabled in this increment.

## Six registered specialists

1. `legislation_researcher` — legislation, provisions, commencement and amendment research.
2. `case_law_researcher` — judgments, holdings, cited authorities and paragraph references.
3. `jurisdiction_analyst` — court hierarchy, territorial and subject-matter jurisdiction.
4. `legal_risk_analyst` — uncertainty, conflict, missing evidence and risk questions.
5. `memo_writer` — organizes supplied findings into a memo-ready structure without adding unsupported law.
6. `critic_reviewer` — checks completeness, traceability, contradictions and unsupported assertions.

Each specialist implements the shared `SpecialistAgent` interface and returns the common `AgentResult` / `AgentFinding` contract. The registry is allow-listed; arbitrary module names cannot be loaded.

## Supervisor

`run_mock_supervisor`:
- Loads a saved research snapshot and its evidence records.
- Builds a bounded, shared `AgentTask`.
- Runs the selected registered specialists sequentially.
- Isolates individual specialist failures so one failure does not prevent other specialists from running.
- Persists the supervisor run and each specialist output.
- Records execution mode as `mock`.
- Preserves evidence IDs in findings so outputs can be traced back to snapshot evidence.

This is a deterministic sequential supervisor foundation, not LangGraph or parallel agent execution.

## API

- `GET /research/agents` — list the six registered specialists and confirm mock mode.
- `POST /research/snapshots/{snapshot_id}/agents/execute` — execute all six mock agents, or a selected subset.
- `GET /research/agent-runs/{run_id}` — retrieve the persisted run and specialist outputs.

The POST body is:

```json
{
  "tenant_id": "YOUR_WORKSPACE_TENANT_ID",
  "agent_keys": [
    "legislation_researcher",
    "case_law_researcher",
    "jurisdiction_analyst",
    "legal_risk_analyst",
    "memo_writer",
    "critic_reviewer"
  ]
}
```

Omit `agent_keys` to run all six.

## Database

Migration `0014_research_agent_runs` follows `0013_research_snapshots`.

New tables:
- `research_agent_runs`
- `research_agent_outputs`

On PostgreSQL, the migration enables and forces RLS, creates tenant-access policies using transaction-local `app.user_id`, and grants `jurismind_app` SELECT and INSERT only.

## Security and reliability boundaries

- API execution requires the existing authenticated JurisMind user and workspace membership.
- Viewer role cannot execute agents.
- Snapshot ID and tenant ID are both checked before execution.
- Run/output records carry tenant IDs and are protected by RLS.
- Agent registry is explicit and allow-listed.
- Agent outputs are marked `execution_provider=mock`.
- No network provider, OpenAI SDK, API key, model call or paid LLM operation is used.
- Agents cannot certify citation identity, pinpoint existence, current law or proposition-to-source support. Increment 9's deterministic citation verification remains a separate layer.
- Mock outputs are framework test artifacts, not legal advice, findings of law or substantive legal research.

## Enablement boundary for a later increment

Real LLM execution must be a separate explicit stage. It should introduce a provider adapter, prompt/version management, strict structured-output validation, token/cost budgets, timeouts/retries, logging/redaction, user approval and deterministic citation verification after model output. Do not simply change a configuration flag to enable paid calls.

## Setup and validation

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m alembic current
python -m pytest -q
python -m uvicorn app.main:app --reload
```

Expected Alembic revision: `0014_research_agent_runs (head)`.

Swagger endpoints appear under `specialist-agents`. Live execution requires working Supabase/JurisMind authentication and an existing research snapshot; the Increment 8 authentication issue remains carried forward.
