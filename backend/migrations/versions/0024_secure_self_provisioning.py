"""Add a narrowly scoped, verified-identity self-provisioning function.

Revision ID: 0024_secure_self_provisioning
Revises: 0023_professional_platform
"""
from alembic import op

revision = "0024_secure_self_provisioning"
down_revision = "0023_professional_platform"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # SECURITY DEFINER is intentionally owned by the migration/admin role.
    # The function accepts only the identity placed in a transaction-local
    # setting by FastAPI after validating the Supabase JWT. The runtime role
    # receives EXECUTE, never direct INSERT/UPDATE rights on identity tables.
    op.execute("""
    CREATE OR REPLACE FUNCTION public.provision_jurismind_user(
        p_supabase_user_id uuid, p_email text, p_workspace_name text
    ) RETURNS TABLE(app_user_id text, tenant_id text)
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = public, pg_temp
    AS $$
    DECLARE v_user_id text; v_tenant_id text; v_context text;
    BEGIN
      v_context := NULLIF(current_setting('app.supabase_user_id', true), '');
      IF v_context IS NULL OR v_context::uuid <> p_supabase_user_id THEN
        RAISE EXCEPTION 'verified identity context mismatch' USING ERRCODE = '42501';
      END IF;
      IF p_email IS NULL OR length(trim(p_email)) < 5 OR length(p_email) > 320 THEN
        RAISE EXCEPTION 'invalid email';
      END IF;
      INSERT INTO public.app_users(id, supabase_user_id, email, created_at)
      VALUES (gen_random_uuid()::text, p_supabase_user_id, lower(trim(p_email)), now())
      ON CONFLICT (supabase_user_id) DO UPDATE
        SET email = EXCLUDED.email
      RETURNING id INTO v_user_id;
      SELECT m.tenant_id INTO v_tenant_id
        FROM public.tenant_memberships m
       WHERE m.user_id = v_user_id
       ORDER BY m.created_at ASC LIMIT 1;
      IF v_tenant_id IS NULL THEN
        v_tenant_id := gen_random_uuid()::text;
        INSERT INTO public.tenants(id, name, created_at)
        VALUES (v_tenant_id, left(trim(p_workspace_name), 200), now());
        INSERT INTO public.tenant_memberships(id, tenant_id, user_id, role, created_at)
        VALUES (gen_random_uuid()::text, v_tenant_id, v_user_id, 'owner', now());
      END IF;
      RETURN QUERY SELECT v_user_id, v_tenant_id;
    END;
    $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.provision_jurismind_user(uuid, text, text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.provision_jurismind_user(uuid, text, text) TO jurismind_app")

def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS public.provision_jurismind_user(uuid, text, text)")
