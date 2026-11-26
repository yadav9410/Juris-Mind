# JurisMind — consolidated Release 2 deployment package

This package combines the uploaded project snapshot with the latest retrieval fixes and the official-source discovery foundation. It also adds a purpose-built frontend panel for official-source discovery.

## Included

- Existing FastAPI backend and Streamlit frontend.
- Broader hybrid retrieval and preservation of uncertain document classifications.
- Research worker job-ID handling fix (`claim_next_job` returns a string ID).
- Official-first Indian source registry: India Code, e-Gazette of India, Supreme Court Reports, Allahabad High Court eLegalix (including Lucknow Bench), and the e-Committee judgments portal.
- Authenticated workspace-scoped endpoints:
  - `GET /research/sources?tenant_id=...`
  - `POST /research/discover/official`
- Frontend Official-source discovery panel under Legal Research.
- Connector host validation and redirect/response-size safeguards.

## Important capability boundary

Official-source discovery currently prepares portal entry points and a query for user-mediated searching. It does **not** automatically search those portals, retrieve judgments, or verify citations. The UI and API explicitly communicate this. No CAPTCHA, login, or other access-control bypass is implemented.

Research jobs still search the currently indexed internal corpus. Their output keeps `external_discovery: not_yet_connected` and `verification_status: not_verified`. Do not represent this release as automated external legal research or citation verification.

## Deploy

1. Back up the production database and retain the current Render deployment as a rollback point.
2. Extract this ZIP and replace the repository working tree with its contents; do not copy any `.env` or secret files into the repository.
3. Run backend tests from `backend/`:
   ```bash
   pytest -q tests
   ```
4. Confirm Python compilation:
   ```bash
   python -m compileall -q app tests
   ```
5. Commit and push the complete project to the existing GitHub `main` branch.
6. Let Render deploy the backend and Streamlit deploy the frontend from the same commit.
7. No new database migration is introduced by this consolidated Release 2 package. Do not run a migration solely for this patch.

## Frontend smoke test after deployment

1. Sign in using a non-production test account and confirm workspace provisioning.
2. Open **Legal Research**.
3. Confirm corpus readiness loads.
4. Use **Official-source discovery** with a query such as `IBC Section 7 admission requirements` and select legislation, Gazette, and judgments.
5. Confirm the official portal list appears and every item is marked `manual_search_required`.
6. Open the India Code, e-Gazette, Supreme Court SCR, and Allahabad eLegalix links as applicable.
7. Run an existing internal-corpus research snapshot and inspect its evidence and limitations.
8. Confirm research-job processing and inspect Render logs for worker startup, database identity, and job execution.

## Production safety

- Never commit `.env`, Supabase service-role keys, JWT secrets, database URLs/passwords, access tokens, or production data.
- Use the existing production `APP_DATABASE_URL` and configured `RUN_RESEARCH_WORKER=true` setting only if that worker is intended to run in this Render service.
- Do not alter database grants or credentials as part of this release.
- Treat every retrieved passage as a research lead until original source identity, applicable version, pinpoint, and proposition support have been independently verified.
