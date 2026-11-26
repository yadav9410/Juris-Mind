# Deployment checklist

- [ ] Review backend `.env`/settings requirements and configure all production secrets in the backend host.
- [ ] Provision PostgreSQL and configure distinct migration-owner and application-runtime credentials.
- [ ] Back up the database.
- [ ] Apply Alembic migrations through the trusted migration connection (`alembic upgrade head`).
- [ ] Confirm `/health/ready` is healthy.
- [ ] Configure Supabase Auth email confirmation, redirect URLs and rate limits/CAPTCHA as appropriate for the project.
- [ ] Configure Streamlit Community Cloud secrets using `frontend/.env.example`.
- [ ] Deploy `frontend/app.py` from this repository.
- [ ] Test existing login, new signup, email confirmation and `/auth/provision` using a non-production test account.
- [ ] Verify tenant isolation and RLS/security tests against a dedicated PostgreSQL test database.
- [ ] Never commit `.env`, service-role keys, database passwords, access tokens or production data.

- [ ] Configure `BRAVE_SEARCH_API_KEY` only in the backend service environment to enable official-domain external research.
- [ ] Confirm external searches return only allow-listed official-source domains and preserve original URLs, retrieval timestamps, SHA-256 hashes and page locators.
- [ ] Confirm search results and retrieved documents remain `not_verified` until separate authority and proposition verification is completed.
