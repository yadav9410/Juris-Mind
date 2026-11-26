# JurisMind Increment 21 — Legal Drafting & Document Generation

This increment adds a tenant-scoped legal drafting workspace to the existing Increment 20 codebase.

## Included
- Structured drafts for legal opinions, memoranda, pleadings, applications, notices, contracts, due-diligence reports, research notes and other documents.
- Section-based draft content and explicit source-reference fields.
- Markdown rendering in the API response for easy copying/export by a later frontend.
- Draft review states: `draft`, `in_review`, `reviewed`, `revision_required`, `final`.
- Reviewer notes and monotonically increasing draft version number.
- Tenant membership checks and PostgreSQL row-level security.
- Migration `0022_legal_drafting_documents`.

## Important scope boundary
This increment stores and renders content supplied by the user or upstream services. It does not autonomously establish legal correctness, validate citations, authenticate authorities, or create a DOCX/PDF file. All propositions, quotations, citations and source references require professional verification. DOCX/PDF export and agent-assisted drafting are future extensions.

## Installation (Windows PowerShell)
1. Stop the API with `Ctrl+C`.
2. Back up your current project folder.
3. Extract this ZIP. Merge the included `app`, `migrations`, `tests`, and `docs` folders into your current project, preserving `.env` and all existing configuration.
4. Activate your existing virtual environment.
5. From the project root, run:

```powershell
python -m alembic upgrade head
python -m pytest -q tests/test_legal_drafting_contract.py
python -m uvicorn app.main:app --reload
```

6. Open `http://127.0.0.1:8000/docs` and find the `legal-drafting` group.

## API endpoints
- `POST /drafting/drafts` — create a draft
- `GET /drafting/drafts?tenant_id=<tenant-id>` — list drafts in a tenant
- `GET /drafting/drafts/{draft_id}` — retrieve a draft and rendered Markdown
- `PATCH /drafting/drafts/{draft_id}` — update sections, source refs, status or reviewer notes

## Example create request

```json
{
  "tenant_id": "YOUR-TENANT-ID",
  "title": "Legal Opinion — Sample Matter",
  "document_type": "legal_opinion",
  "jurisdiction": "India",
  "matter_reference": "MAT-001",
  "sections": [
    {"heading": "Question Presented", "content": "State the legal question.", "source_refs": []},
    {"heading": "Brief Answer", "content": "Draft answer subject to source verification.", "source_refs": []},
    {"heading": "Analysis", "content": "Set out the analysis and counterarguments.", "source_refs": ["source-id-or-citation"]}
  ],
  "source_refs": ["source-id-or-citation"]
}
```

## Verification status
The package should be treated as an integration increment. The two contract tests check that the routes are exposed in OpenAPI; they do not replace database migration execution or end-to-end authenticated API testing against the user's PostgreSQL environment.
