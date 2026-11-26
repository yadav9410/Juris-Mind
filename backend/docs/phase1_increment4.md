# Phase 1 — Increment 4: PostgreSQL security validation and tenant management

## What this increment adds

- A PostgreSQL migration constraining workspace roles to `owner`, `admin`, `member`, and `viewer`.
- Row-level security for tenant-scoped audit events.
- A documented Neon/PostgreSQL validation procedure and SQL checks.
- An integration-test scaffold that is enabled only when `TEST_DATABASE_URL` points to PostgreSQL.
- A role-permission matrix and safe tenant-management workflow recommendations.

## Important security boundary

The existing `0002_tenant_security_policies.py` migration applies RLS to `tenants` and `tenant_memberships`. This increment does not claim that all private data is protected: currently `audit_events` is the only tenant-scoped private repository model in the initial schema. When private uploads, research sessions, memos, and generated files are added, each tenant-owned table and object-storage operation must receive equivalent controls and tests.

Public legal corpus tables (`legal_works`, `source_records`, `legal_documents`, `document_versions`, `legal_provisions`, `judgment_paragraphs`, and `document_events`) are intentionally shared. Do not add tenant filtering to these shared public records unless a separate private overlay is introduced.

## Role baseline

| Role | Read workspace | Manage members | Manage workspace settings | Create/edit research | Delete/export sensitive data |
|---|---:|---:|---:|---:|---:|
| owner | Yes | Yes | Yes | Yes | Yes |
| admin | Yes | Yes | Yes | Yes | Policy-controlled |
| member | Yes | No | No | Yes | No by default |
| viewer | Yes | No | No | No | No |

The database constraint validates role names only. API-level authorization for each action must be implemented before exposing these operations.

## Configure PostgreSQL (Neon)

1. Create or select a Neon PostgreSQL project using the account's available free tier. Check current quota, expiry/suspend behaviour, backup/restore and billing settings in the Neon dashboard; free-tier terms can change.
2. Copy the pooled or direct connection string as appropriate. For Alembic migrations, prefer the direct connection string if the provider recommends it; use the pooled URL for application traffic only where supported.
3. Put the URL in `.env` as `DATABASE_URL`. Do not commit `.env` or share the connection string.
4. Create a separate least-privilege application role for runtime traffic. Do not use the Neon owner/superuser role in the application.
5. Apply migrations: `alembic upgrade head`.
6. Check migration state: `alembic current` (expected head: `0003_role_audit_rls`).

## Required PostgreSQL role checks

Run the following in the SQL editor while connected as the runtime application role (not the database owner):

```sql
SELECT current_user,
       rolsuper,
       rolbypassrls
FROM pg_roles
WHERE rolname = current_user;
```

Both `rolsuper` and `rolbypassrls` must be false. Also verify RLS is enabled and forced:

```sql
SELECT n.nspname AS schema_name,
       c.relname AS table_name,
       c.relrowsecurity AS rls_enabled,
       c.relforcerowsecurity AS rls_forced
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relname IN ('tenants', 'tenant_memberships', 'audit_events');
```

All three should show `true` for both RLS columns. Verify policies:

```sql
SELECT tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE tablename IN ('tenants', 'tenant_memberships', 'audit_events')
ORDER BY tablename, policyname;
```

## Test procedure

Install dependencies and set `TEST_DATABASE_URL` to a disposable PostgreSQL database:

```bash
pip install -r requirements.txt
pytest -q
```

The normal test suite includes SQLite unit tests. PostgreSQL-only integration tests are skipped unless `TEST_DATABASE_URL` is set. Use a disposable database; tests may create and remove test tables. Never point destructive tests at production data.

## Current limitation / go-no-go

This increment adds a role-name constraint and audit-event RLS, but it does not yet implement full workspace creation/invitations or role-checked member-management endpoints. The existing tenant RLS policies also require careful integration validation with the actual runtime database role. Do not upload confidential client documents until PostgreSQL isolation and object-storage isolation are both demonstrated by passing tests.
