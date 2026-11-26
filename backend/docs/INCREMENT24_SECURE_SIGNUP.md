# Increment 24 — Secure sign-up and first-time provisioning

## What changed

- Added `POST /auth/provision`, which accepts only a Supabase JWT verified by the existing JWKS verifier.
- The endpoint provisions only the JWT subject and requires the submitted email to match the verified token email.
- Added a PostgreSQL `SECURITY DEFINER` function in migration `0024_secure_self_provisioning`. The runtime role receives `EXECUTE` on that function, not direct write privileges on `app_users` or `tenant_memberships`.
- New users receive a personal workspace and `owner` membership. Existing users are handled idempotently and retain their existing first membership/workspace.
- Added `GET /auth/me` for the provisioned account identity.
- Added a Streamlit sign-up tab while retaining sign-in. Sign-in also invokes idempotent provisioning so email-confirmation flows complete after the user returns and authenticates.

## Deployment

1. Back up the database.
2. Confirm the migration connection (`DATABASE_URL`) is a trusted migration/admin role that owns the identity tables and can create a `SECURITY DEFINER` function. Do not use the runtime `jurismind_app` role for migrations.
3. Apply migrations through `0024_secure_self_provisioning` using the existing deployment procedure (`alembic upgrade head`).
4. Confirm the runtime role is `jurismind_app`, and that it has the expected `EXECUTE` privilege on `public.provision_jurismind_user(uuid,text,text)`. It must not have direct write privileges on identity or membership tables.
5. Keep Supabase email confirmation and CAPTCHA/rate-limit settings configured in the Supabase Auth dashboard according to the deployment's abuse model.
6. Deploy the updated API and Streamlit frontend.

## Important behavior

- The public Supabase publishable/anon key remains in the frontend; never put a Supabase service-role key there.
- The endpoint rejects anonymous JWTs and does not accept a caller-supplied Supabase user ID.
- If Supabase email confirmation is enabled, sign-up may return no access token. The user confirms the email, signs in, and provisioning then completes.
- Existing provisioned users can safely call provisioning again; their existing workspace membership is retained.
- This increment does not implement guest chat or chat persistence.

## Validation

Python source compilation and AST parsing passed. The full pytest collection is currently blocked because the repository contains `scripts/test_app_user_rls.py`, which raises during collection when `APP_DATABASE_URL` is not set. No live PostgreSQL migration or Supabase Auth integration test was run in this environment.
