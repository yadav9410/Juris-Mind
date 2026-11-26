# Tenant management workflow — design contract

These are the rules to implement in the next increment; they are not yet exposed as public API operations.

1. A verified Supabase `sub` is the only source of user identity. Never accept a user ID from request JSON as the acting identity.
2. Workspace creation must be one atomic database operation: create tenant, create the creator's `owner` membership, and write an audit event. If any step fails, roll back all steps.
3. Invitations must be bound to a tenant, expire, be single-use, and be accepted by the authenticated invitee. Do not let a caller self-assign `owner` or `admin`.
4. Only `owner`/`admin` may invite members or change non-owner roles. Ownership transfer and owner removal need a separate explicit workflow.
5. Enforce role checks in service/API code and tenant row policies in PostgreSQL. RLS is defence in depth, not a substitute for authorization.
6. Set `app.user_id` transaction-locally on every request transaction before tenant-scoped queries. Never use a session-persistent setting that can leak across pooled connections.
7. Shared public legal corpus records remain globally readable. Private documents and future memo/research tables must be tenant-scoped.
8. Object-storage keys and signed URL issuance must independently verify tenant ownership; database RLS does not protect R2 objects.
9. Log membership changes, invitations, role changes, exports and deletion attempts without logging tokens, document contents or secrets.
