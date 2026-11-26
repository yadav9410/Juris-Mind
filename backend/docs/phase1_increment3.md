# Phase 1 — Increment 3: Authentication and Tenant Security Foundations

## Included
- Supabase asymmetric JWT verification through the project's JWKS endpoint.
- Required signature, issuer, audience, expiry and subject validation.
- Protected example endpoint: `GET /tenants/{tenant_id}/access-check`.
- Server-side membership check; tenant IDs supplied by callers are not treated as authorization.
- PostgreSQL RLS migration for `tenants` and `tenant_memberships`.
- Transaction-local `app.user_id` context used by those policies.
- Tests for member access, non-member denial and cross-tenant denial.

## Configuration
Set `SUPABASE_URL` to the project URL in `.env`. The verifier uses the Supabase JWKS endpoint at `/auth/v1/.well-known/jwks.json`. The Supabase project must issue asymmetric ES256 or RS256 access tokens for this implementation. Legacy HS256 projects require a separately reviewed verifier; this code deliberately does not silently fall back to an HMAC secret.

## Migration
Run `alembic upgrade head`. Migration 0002 applies RLS only on PostgreSQL; SQLite skips it because SQLite has no RLS feature.

## Important deployment requirements
- The API database role must not be a superuser and must not have `BYPASSRLS`.
- Test RLS using the actual application database role, not the migration owner.
- Set `app.user_id` within each transaction before querying tenant-protected tables.
- Keep public legal corpus tables separate from tenant-private records; this migration protects only tenants and memberships.
- Supabase JWT verification and tenant membership checks do not replace rate limiting, session revocation strategy, audit review, or security testing.
- Do not use confidential client documents until PostgreSQL RLS, storage authorization and end-to-end isolation tests pass.
