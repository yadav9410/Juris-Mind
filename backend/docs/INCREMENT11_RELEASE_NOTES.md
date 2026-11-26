# Increment 11 Release Notes

**Feature:** Specialist Legal Research Agents & Supervisor Foundation  
**Database revision:** `0014_research_agent_runs`  
**Execution mode:** Mock only

### Included
- Six specialist-agent modules.
- Shared task, evidence, finding and result contracts.
- Allow-listed agent registry.
- Sequential supervisor with per-agent failure isolation.
- Evidence-linked mock outputs.
- Persistent agent-run and agent-output records.
- Authenticated API routes for listing agents, executing a run and retrieving outputs.
- PostgreSQL RLS and restricted SELECT/INSERT runtime grants.
- Mock-first automated tests.

### Explicitly not enabled
- OpenAI or any other real LLM provider.
- External network calls from agents.
- Paid API usage.
- Autonomous legal conclusions or citation certification.
- Parallel/LangGraph orchestration.
