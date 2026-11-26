# JurisMind Increment 14 — Claim-to-Evidence Assessment

## Purpose

Increment 14 builds on the existing Increment 9 citation identity/pinpoint checks and Increment 13 evidence retrieval. It adds a persisted, workspace-scoped assessment that compares a stated legal proposition with supplied source passages.

## Included

- Deterministic token normalization and overlap scoring.
- Per-passage candidate-support, weak-overlap, or no-material-overlap labels.
- Claim term coverage, matched terms, source label, locator, page, and excerpt in the report.
- Persisted assessment history in `research_claim_assessments`.
- Authenticated workspace endpoints:
  - `POST /research/claims/assess`
  - `GET /research/claims/{assessment_id}`
- Alembic migration `0015_claim_evidence_assessments`, following `0014_research_agent_runs`.
- PostgreSQL forced RLS and `jurismind_app` SELECT/INSERT grants.

## Important interpretation

This increment is a conservative lexical screening layer, not semantic legal reasoning. `candidate_support` means the passage has substantial word overlap with the claim; it does not establish that the passage entails, legally supports, or is consistent with the claim. Human review of the complete source and context remains mandatory. The endpoint assesses only passages supplied in the request and does not independently retrieve or authenticate them.

The existing `/citations/verify` service remains separate. A matched citation does not establish proposition support; this increment addresses that separate question only as a candidate screening aid.

## Installation

1. Extract this ZIP into a new folder; keep the Increment 13 folder as your rollback baseline.
2. Copy your existing local `.env` into the new project root. Do not upload or commit it.
3. Activate your Python 3.12 virtual environment (or create a new one).
4. Install dependencies: `python -m pip install -r requirements.txt`
5. Apply the migration using the migration/admin database credentials configured for Alembic: `alembic upgrade head`
6. Start the API: `uvicorn app.main:app --reload`

Do not run the migration with the restricted application role if it lacks DDL permissions. No paid service or new external API is required.

## API example

`POST /research/claims/assess`

```json
{
  "tenant_id": "YOUR_WORKSPACE_ID",
  "claim": "The resolution applicant cannot withdraw an approved resolution plan.",
  "evidence": [
    {
      "evidence_id": "snapshot-evidence-1",
      "source_label": "Twinstar Technologies judgment",
      "locator": "paragraph 43",
      "page": 43,
      "text": "Paste the complete relevant passage here."
    }
  ]
}
```

Then retrieve the saved report using `GET /research/claims/{assessment_id}`.

## Test

Run: `python -m pytest -q tests/test_claim_evidence_assessment.py`

Also run the existing suite: `python -m pytest -q tests`.

## Known limitations

- Lexical overlap can miss paraphrases and can over-score passages that repeat words but do not support the proposition.
- Negation, exceptions, procedural posture, ratio/obiter distinctions, and conflicting authorities are not resolved.
- Evidence provenance fields are supplied by the caller; this API does not validate evidence IDs against snapshot records in this increment.
- Citation extraction/matching and authority status continue to have the limitations documented in Increment 9.
- No live Neon/Supabase/OpenAI/legal-source integration test is performed by the automated unit tests.


## Indicative roadmap after Increment 14

These are proposed future increments, not implemented in this ZIP. Their exact scope may be refined after each acceptance test.

- **Increment 15 — Source Provenance & Evidence Integrity:** connect assessment evidence to immutable snapshot/chunk records; retain source/version/hash/locator lineage and reject caller-supplied identifiers that do not belong to the workspace.
- **Increment 16 — Legal Authority Treatment & Currentness:** build a sourced treatment graph for followed, distinguished, overruled, doubted, affirmed, amended and repealed authorities, with event provenance and effective dates.
- **Increment 17 — Statutory Versioning & Temporal Law:** improve Act/rule amendment timelines, commencement tracking and “law as of date” reconstruction.
- **Increment 18 — Research Memo Generation:** generate structured legal research notes and due-diligence memos from frozen snapshots, verified citations and reviewed claim-evidence links.
- **Increment 19 — Quality Review & Adversarial Testing:** add contradiction detection, counter-authority searches, jurisdiction checks, reviewer workflows and benchmark datasets.
- **Increment 20 — Workspace Product & Document Workflow:** add document upload/review UX, memo export/versioning, approvals, audit views and collaboration controls.
- **Increment 21 — Deployment & Operational Hardening:** R2-backed storage, production deployment checks, monitoring, backups, rate limits, security tests and recovery procedures.

