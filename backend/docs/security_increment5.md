# JurisMind Security Increment 5 — Identity, Database & Tenant Isolation

## Included
- Adds nullable unique `app_users.supabase_user_id` for trusted Supabase-to-JurisMind identity linking.
- JWT validation requires signature, issuer, audience, expiry and UUID subject.
- Authentication resolves the verified external subject to a pre-provisioned internal `app_users.id`; no email-based auto-provisioning.
- Tenant membership checks use the internal JurisMind ID.
- PostgreSQL runtime session uses `APP_DATABASE_URL`; Alembic continues to use `DATABASE_URL`; ingestion continues to use `INGESTION_DATABASE_URL`.
- Migration 0008 revokes direct authenticated/anon and app-role writes to identity/membership tables, and installs SELECT-only RLS policies for the application role.

## Required environment configuration
`DATABASE_URL` = migration/admin `neondb_owner` connection.
`APP_DATABASE_URL` = runtime `jurismind_app` connection.
`INGESTION_DATABASE_URL` = ingestion `jurismind_ingest` connection.
`SUPABASE_URL` = Supabase project URL.

Do not paste connection strings or passwords into chat. Set these only in the local `.env` or deployment secret store.

## Provisioning
A trusted administrator must link an existing Supabase Auth UUID to an existing `app_users` row by setting `supabase_user_id`. Never auto-link based on email. Existing rows remain unlinked until deliberately provisioned.

## Important scope limits
- This increment does not implement tenant invitation, membership mutation, owner appointment or last-owner-protection APIs. Runtime roles are intentionally read-only for identity and membership tables. Those operations require a separately reviewed SECURITY DEFINER function/service and tests before enabling.
- RLS custom GUCs are trusted backend context, not cryptographic proof. The backend must validate JWTs, use parameterized SQL and keep direct database access private. A compromised DB credential can set custom GUCs.
- Existing public staging search is not converted into private tenant search by this increment.
- Migration SQL is PostgreSQL-specific for RLS and role grants; SQLite skips those sections for tests.
- Verify actual role grants and RLS behaviour in Neon after migration. A migration success alone is not proof of full tenant isolation.

## Linking an existing profile (trusted administrator only)
After migration, an authorized provisioning process can link an existing profile using the verified Supabase Auth UUID:

```sql
UPDATE app_users
SET supabase_user_id = '00000000-0000-0000-0000-000000000000'
WHERE id = 'EXISTING_INTERNAL_APP_USER_ID';
```

Replace both placeholders with verified values obtained from the trusted Supabase admin workflow. Run this using the migration/admin connection, never the runtime app role. Do not use email alone to decide the link. The unique constraint prevents one Supabase identity from being linked to multiple JurisMind profiles.

## Neon post-migration checks
Run as an administrator:

```sql
SELECT version_num FROM alembic_version;
SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = 'app_users'::regclass;
SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = 'tenant_memberships'::regclass;
SELECT grantee, privilege_type FROM information_schema.role_table_grants
WHERE table_name IN ('app_users', 'tenant_memberships')
ORDER BY table_name, grantee, privilege_type;
```

Expected migration version: `0008_identity_tenant_isolation`. Confirm that `jurismind_app` has SELECT but no direct INSERT/UPDATE/DELETE on `app_users` and `tenant_memberships`; `authenticated` and `anon` should have no table privileges. RLS should be enabled and forced on both tables. Do not infer complete isolation solely from these catalog checks; exercise the API with two provisioned users in different tenants before deployment.
