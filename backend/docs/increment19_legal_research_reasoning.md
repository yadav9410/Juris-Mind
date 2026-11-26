# Increment 19 — Legal Research & Reasoning Engine

## Included capabilities

Increment 19 builds on the existing hybrid search, research snapshots, claim/evidence assessment, citation verification, authority treatment and judgment intelligence APIs. It adds a workspace-scoped legal reasoning record that organises user-supplied facts, issues, legal elements, supporting/adverse facts, authorities, evidence references, party arguments, supporting reasons and counterarguments.

This is a structured reasoning workspace, not an autonomous legal conclusion engine. It does not independently decide whether a proposition is legally correct, infer a binding ratio, or verify the truth of user-entered facts. Use existing research snapshots, claim assessments, citations and source records as linked research material; human review remains necessary.

## Migration

With the migration/admin database URL configured:

```powershell
python -m alembic upgrade head
```

New migration: `0020_legal_reasoning_workspace` (follows `0019_judgment_intelligence`). PostgreSQL RLS restricts rows to workspace members; writes require owner/admin/member role. The runtime role receives SELECT, INSERT and UPDATE grants.

## New endpoints

- `POST /research/reasoning/workspaces` — create an issue and argument map.
- `GET /research/reasoning/workspaces?tenant_id=<tenant-id>` — list workspaces for a tenant.
- `GET /research/reasoning/workspaces/{workspace_id}` — retrieve a workspace.
- `PATCH /research/reasoning/workspaces/{workspace_id}/review` — update review status and notes.

All routes require the existing Bearer authentication and workspace membership.

## Example request

```json
{
  "tenant_id": "YOUR-TENANT-ID",
  "title": "Contract termination dispute",
  "fact_summary": "Summarise the material facts and procedural history here.",
  "linked_snapshot_id": null,
  "linked_assessment_ids": [],
  "issues": [
    {
      "issue": "Whether termination complied with the contract",
      "legal_test_or_elements": ["Applicable notice clause"],
      "facts_supporting": ["Notice was served"],
      "facts_against": ["Notice period may have been short"],
      "authorities": [],
      "evidence_refs": ["document-id/page-4"],
      "status": "open"
    }
  ],
  "arguments": [
    {
      "issue_index": 0,
      "side": "claimant",
      "proposition": "Termination was contractually invalid",
      "supporting_reasons": ["The notice period was insufficient"],
      "authority_refs": [],
      "evidence_refs": ["document-id/page-4"],
      "counterarguments": ["The contract may permit immediate termination"]
    }
  ]
}
```

`issue_index` is zero-based and must refer to an issue in the same request. The service validates structure and workspace access; it does not verify whether the legal analysis or source references are correct.

## Installation

1. Back up the existing project.
2. Extract this ZIP and merge its `app`, `migrations`, `tests` and `docs` folders into the existing project. Do not replace `.env` or your existing database settings.
3. Keep your existing virtual environment active and install only if needed: `python -m pip install -r requirements.txt`.
4. Apply the migration: `python -m alembic upgrade head`.
5. Run the focused tests: `python -m pytest -q tests/test_legal_reasoning_contract.py`.
6. Restart the API: `python -m uvicorn app.main:app --reload`.
7. Open `/docs` and look for the `legal-reasoning-workspace` tag.

## Known boundaries

- The workspace stores structured human-authored issues and arguments; it does not generate legal advice automatically.
- Linked snapshot and assessment identifiers are references, not an assertion that the linked records support the issue. Open and review those records separately.
- Existing research retrieval remains limited to the indexed corpus and its current coverage.
- PostgreSQL RLS behavior depends on the existing runtime identity context and role grants; validate on the configured database during installation.
