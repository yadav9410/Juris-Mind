# JurisMind — combined GitHub repository

JurisMind is an Indian-law-focused legal intelligence platform with a FastAPI backend and a Streamlit frontend.

## Repository layout

- `backend/` — FastAPI application, SQLAlchemy models, Alembic migrations, API routes and tests.
- `frontend/` — Streamlit application and Supabase authentication client.

This repository keeps the two services together for version control. **They are deployed as two services:** Streamlit Community Cloud runs the frontend; it does not host the FastAPI API process.

## Current capabilities

The repository preserves the existing research, statutory intelligence, judgment intelligence, reasoning, due-diligence, drafting, evidence and matter-management modules. Increment 24 adds Supabase sign-up and verified backend provisioning for a new user's JurisMind profile and personal workspace. Existing sign-in is retained.

The current release does not include the separately planned guest chat / non-persistent chat workflow. Do not treat guest chat as available until a later release adds and tests it.

## 1. Prerequisites

- Python 3.11 or newer (use the same supported Python version for both services).
- A Supabase project.
- A PostgreSQL database configured for the backend.
- A deployment service for the FastAPI backend.
- A Streamlit Community Cloud app connected to this GitHub repository.

## 2. Backend configuration

Create `backend/.env` locally, or set the equivalent environment variables in your backend hosting provider. Never commit secrets.

Use the backend settings documented in `backend/README.md` and `backend/app/core/config.py`. At minimum, configure the PostgreSQL database URL and Supabase JWT verification settings required by the backend. Keep the migration/owner database credentials separate from the restricted runtime database role.

Install and migrate:

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

Start locally:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check: `/health/ready` (if the readiness endpoint reports a database or configuration issue, resolve it before connecting the frontend).

### Render deployment example

A `render.yaml` is included as a starting point for deploying the backend on Render. Set all required environment variables and secrets in the Render dashboard. Confirm that the selected database URL, migration role, and runtime role match your production security design before deployment.

## 3. Frontend configuration

The frontend reads configuration from Streamlit secrets or environment variables. For Streamlit Community Cloud, open **App → Settings → Secrets** and add:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"
JURISMIND_API_URL = "https://YOUR-BACKEND-HOST"
JURISMIND_REQUEST_TIMEOUT = "30"
```

Do not put a Supabase `service_role` key in the frontend. The frontend must use only the publishable/anon key. Backend provisioning is performed by the authenticated API and database function.

For local development, copy `frontend/.env.example` to `frontend/.env`, fill in the values, and run:

```bash
cd frontend
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## 4. Deploy the Streamlit app from GitHub

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, choose **Create app**.
3. Select this repository and branch.
4. Set the main file path to `frontend/app.py`.
5. Add the frontend secrets shown above.
6. Deploy. The FastAPI backend must already be deployed and reachable at `JURISMIND_API_URL`.

## 5. Signup and provisioning flow

1. A user creates an account through Supabase Auth.
2. If Supabase email confirmation is enabled, the user confirms their email and then signs in.
3. The frontend sends the signed-in access token to `POST /auth/provision`.
4. The backend verifies the token and checks that the requested email matches the verified identity.
5. The database provisioning function creates or returns the internal JurisMind user, personal workspace and owner membership.
6. Existing users and memberships are not replaced by the signup flow.

Apply Alembic migrations with a trusted migration/owner connection, not the restricted application runtime role.

## 6. Validation

Run backend tests from `backend/`:

```bash
pytest
```

Some integration/security tests require a configured PostgreSQL test database (see the test configuration and README in `backend/`). A syntax check is not a substitute for a live Supabase/PostgreSQL integration test.

## Legal-use notice

JurisMind provides AI-generated legal information for research and educational purposes. It is not legal advice, does not create an advocate-client relationship, and does not guarantee that answers are complete or current. Verify legal authorities against authentic sources and consult a qualified advocate before acting. Avoid submitting confidential, privileged or sensitive information unless you have assessed the applicable data-handling arrangements.
