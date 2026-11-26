# JurisMind — Complete Streamlit Frontend

A standalone Streamlit UI for the existing JurisMind FastAPI backend (Increment 22). It does not modify the backend or require a database migration.

## Features
- Existing Supabase email/password authentication.
- Access token sent to FastAPI using Bearer authentication.
- Sign-out revokes the Supabase session where possible and clears local session state.
- Polished dashboard with API readiness, protected API and legal corpus checks.
- Navigation for legal research, statutory intelligence, judgment intelligence, legal reasoning, due diligence, drafting, matter management, agents/evidence.
- Dynamic API workbench built from the backend's live `/openapi.json` schema. Forms are generated from endpoint parameters and Pydantic request schemas, so endpoints remain aligned with the installed backend.
- Request/response viewer and endpoint filtering.
- Local environment configuration; no credentials embedded in code.

## Prerequisites
- Python 3.11 or later.
- Increment 22 FastAPI backend running.
- Existing Supabase project URL and publishable/anon key.
- Existing Supabase user provisioned in JurisMind `app_users`; API access is still subject to backend tenant membership/RLS.

## Windows PowerShell installation
1. Extract the ZIP to a separate folder, e.g. `C:\JurisMind\frontend`.
2. Open PowerShell in that folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

3. Set values in `.env`:

```dotenv
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_EXISTING_SUPABASE_PUBLISHABLE_OR_ANON_KEY
JURISMIND_API_URL=http://127.0.0.1:8000
JURISMIND_REQUEST_TIMEOUT=30
```

Use the same Supabase project as the backend. Do not use a service-role key. Do not commit `.env`.

4. Start the backend in its own terminal, from its existing project:

```powershell
python -m uvicorn app.main:app --reload
```

5. Start the frontend from this folder:

```powershell
python -m streamlit run app.py
```

6. Open the URL printed by Streamlit, normally `http://localhost:8501`.

## GitHub setup
Initialize Git in the frontend folder only:

```powershell
git init
git add .
git commit -m "Initial JurisMind Streamlit frontend"
```

Create an empty GitHub repository and follow its instructions to add the remote and push. Check `git status` and ensure `.env` is ignored before committing.

## Troubleshooting
- Supabase sign-in failure: verify URL, publishable/anon key, email/password and Supabase Auth settings.
- API 401: sign in again; check JWT issuer/JWKS configuration in backend.
- API 403 / "JurisMind account is not provisioned": confirm the Supabase UUID maps to a provisioned `app_users.supabase_user_id`.
- API unavailable: confirm backend is running and `JURISMIND_API_URL` points to it.
- Endpoint list missing: use "Refresh API schema" in sidebar. The UI reads `/openapi.json` from the live backend.
- For remote deployment, configure HTTPS and store secrets in the hosting provider's secret manager. Do not expose local `.env` or service-role credentials.

## Scope and limitations
- This is the complete first-pass Streamlit interface for the backend routes exposed in OpenAPI. It is not a custom, fully bespoke screen for every legal workflow; forms are schema-driven to cover the full API surface accurately.
- Existing backend routes that are not exposed in OpenAPI (for example compatibility routes marked `include_in_schema=False`) are intentionally not shown.
- The UI does not create or provision Supabase users or tenant memberships.
- Backend permissions, tenant isolation and legal review requirements remain enforced by the API.
- Local syntax compilation and ZIP integrity are checked; live Supabase login and end-to-end API actions must be verified in your environment.
