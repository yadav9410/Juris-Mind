# JurisMind Increment 20 — Legal Due-Diligence & Risk Engine

This package builds on the supplied Increment 19 repository. It adds tenant-scoped due-diligence matters, a structured risk register and document-comparison records.

## Included capabilities

- Corporate, transaction, litigation, regulatory and general due-diligence matters.
- Scope capture and matter listing.
- Risk register with user-entered likelihood and impact (1–5); severity is calculated from likelihood × impact.
- Evidence reference strings, recommendations, mitigation owner and status.
- Document version comparison records with structured change entries and human-review status.
- Tenant membership checks and PostgreSQL row-level security.
- Alembic migration `0021_due_diligence_risk_engine`.

Risk scoring is a prioritisation aid only. The system does not independently determine legal risk, materiality, authenticity, or the legal effect of document changes. Evidence references are recorded as supplied; they are not independently validated by this increment.

## Install (Windows PowerShell)

1. Stop the running API with `Ctrl+C`.
2. Back up your current JurisMind project folder and database.
3. Extract this ZIP. It contains the complete source tree from the uploaded Increment 19 ZIP (excluding the local `venv` and caches), plus Increment 20 changes.
4. Use the extracted project folder as the working project, or merge `app`, `migrations`, `tests` and this README into the existing project. Preserve your `.env` and do not overwrite local secrets.
5. Activate the existing virtual environment.
6. Run:

```powershell
python -m alembic upgrade head
python -m pytest -q tests/test_due_diligence_contract.py
python -m uvicorn app.main:app --reload
```

7. Open `http://127.0.0.1:8000/docs` and find the `due-diligence-risk` group.

## New endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/due-diligence/matters` | Create a due-diligence matter |
| GET | `/due-diligence/matters?tenant_id=...` | List tenant matters |
| GET | `/due-diligence/matters/{matter_id}` | Retrieve a matter |
| POST | `/due-diligence/matters/{matter_id}/risks` | Add a risk |
| GET | `/due-diligence/matters/{matter_id}/risks` | List risks |
| POST | `/due-diligence/matters/{matter_id}/comparisons` | Record document comparison |
| GET | `/due-diligence/matters/{matter_id}/comparisons` | List comparisons |

The migration has not been applied to your live database by packaging this ZIP. It will run when you execute `alembic upgrade head`.
