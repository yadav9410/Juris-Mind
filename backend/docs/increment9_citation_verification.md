# JurisMind Increment 9 — Legal Citation & Authority Verification Engine

## Purpose

Increment 9 adds a conservative, deterministic first-pass engine for identifying citation-shaped text, normalizing common Indian citation formats, matching candidates to the legal repository, checking structured pinpoints, and recording evidence-linked verification outcomes.

It deliberately does **not** claim that a citation is legally correct merely because a text match exists.

## Included functionality

- Rule-based extraction for:
  - Indian neutral citations in the form `YYYY INSC NNN`;
  - SCC citations such as `(1979) 2 SCC 409`;
  - selected AIR court-report formats;
  - SCR citation-shaped strings;
  - statutory references such as `Section 3(2)`, `Article 14`, and `Rule 5`.
- Exact source offsets and original citation wording are retained.
- Normalized fields are stored separately from the raw citation text.
- Statutory references are matched against `legal_provisions.provision_ref`.
- Case citations are matched against repository `legal_works.canonical_identifier` and title fields.
- Multiple matches are returned as `ambiguous`; no arbitrary winner is selected.
- Pinpoint checks use provision references or structured judgment paragraph numbers where available.
- Authority status is based only on recorded `document_events`; absent evidence is `unknown`.
- Citation candidates and verification runs are persisted in workspace-scoped tables.
- API endpoints:
  - `POST /citations/verify`
  - `GET /citations/{citation_id}`

## Migration

New Alembic revision: `0012_citation_verification`, following `0011_human_metadata_review`.

The migration creates `citation_references` and `verification_records`, adds indexes, and enables forced RLS on PostgreSQL. The API role receives SELECT/INSERT only; it does not receive UPDATE/DELETE grants through this migration.

## API example

`POST /citations/verify`

```json
{
  "tenant_id": "YOUR_WORKSPACE_TENANT_ID",
  "source_label": "Draft legal memo",
  "text": "The issue was considered in 2024 INSC 123. See also Section 3(2).",
  "pinpoints": {
    "Section 3(2)": "Section 3(2)"
  }
}
```

The API returns each extracted citation, normalized fields, repository match status, pinpoint status, authority status, and evidence.

## Status meanings

| Field | Values | Meaning |
|---|---|---|
| `verification_status` | `matched`, `ambiguous`, `not_found` | Repository identity lookup result |
| `pinpoint_status` | `verified`, `not_found`, `unverifiable`, `not_applicable` | Whether a requested pinpoint exists in structured repository data |
| `authority_status` | `unknown`, `amended`, `repealed`, `overruled`, `recorded_as_in_force`, `affirmed_event_recorded` | Limited status derived from recorded repository events |

`recorded_as_in_force` means only that an enactment/commencement event is recorded and no later recognized event was found in the repository query. It is not a complete legal currentness opinion.

## Known limitations

1. Citation patterns are deliberately limited and heuristic. They will not identify every Indian reporter, court abbreviation, parallel citation, party-name citation, foreign citation, or malformed citation.
2. The initial AIR pattern supports a selected set of court codes; expand only with test fixtures.
3. Citation extraction does not infer case party names from surrounding prose.
4. Case matching depends on `canonical_identifier` or title values actually populated in `legal_works`. It is not fuzzy or web-based.
5. Statutory matching checks the provision reference, not the Act title in the surrounding sentence. Identical section numbers in multiple Acts may therefore be ambiguous.
6. Judgment pinpoint verification requires populated `judgment_paragraphs`; page references alone are not treated as paragraph verification.
7. Authority status is only as complete as `document_events`. Absence of an event is not proof of current validity. Subsequent treatment such as distinguished, doubted, or followed is not inferred.
8. A verified pinpoint is not proof that the passage supports the proposition for which it is cited.
9. This increment does not resolve Increment 8's known authenticated metadata-review API issue.

## Local setup and validation

From the project root in PowerShell:

```powershell
# Activate the existing Python 3.12 virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies if needed
python -m pip install -r requirements.txt

# Apply the new migration using the configured migration DATABASE_URL
python -m alembic upgrade head

# Run the complete test suite
python -m pytest -q
```

For a local API smoke test, start the service:

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`, authenticate using the existing Supabase bearer-token workflow, and test `POST /citations/verify`.

The API is authenticated and requires an existing provisioned JurisMind user with workspace membership. Increment 8's known provisioning/lookup issue may prevent API-level smoke testing in the current environment. The parser and verification service are independently unit-testable.

## Operational cautions

- Back up the database before applying migrations.
- Run the migration with the dedicated migration/admin connection, not the restricted runtime connection.
- Do not grant the runtime role table ownership or RLS bypass.
- Do not insert sample legal authorities into production merely to make a demo match.
- Treat all results as review aids, not legal advice or a substitute for checking primary source documents.
