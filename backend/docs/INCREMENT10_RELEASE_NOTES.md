# Increment 10 Release Notes

**Feature:** Legal Research Orchestration & Research Snapshots  
**Database revision:** `0013_research_snapshots`  
**API namespace:** `/research`

### Included
- Deterministic research planning and optional user-supplied sub-questions.
- Multi-query retrieval through the existing hybrid legal search service.
- Workspace-scoped research snapshots and frozen evidence records.
- Authenticated create, list and retrieve endpoints.
- Viewer read-only enforcement for snapshot creation.
- PostgreSQL forced RLS policies and restricted runtime grants.
- Unit, persistence and API contract tests.

### Not included
- Six specialist agents or LLM supervisor execution.
- Semantic/vector retrieval.
- Legal conclusion generation or proposition-to-passage entailment.
- Automatic citation/authority certification.
- Resolution of Increment 8's deferred authentication issue.
