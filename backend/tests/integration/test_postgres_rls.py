"""PostgreSQL-only RLS smoke tests.

Run only against a disposable PostgreSQL database via TEST_DATABASE_URL.
These tests validate database policy behaviour, not the entire API stack.
"""
import os
import pytest
from sqlalchemy import create_engine, text

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL or not TEST_DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg://")),
    reason="Set TEST_DATABASE_URL to a disposable PostgreSQL database to run RLS tests.",
)


def test_postgres_has_forced_rls_on_tenant_tables():
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT relname, relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname IN ('tenants', 'tenant_memberships', 'audit_events')
            """)).all()
            found = {row[0]: (row[1], row[2]) for row in rows}
            assert set(found) == {"tenants", "tenant_memberships", "audit_events"}
            assert all(enabled and forced for enabled, forced in found.values())
    finally:
        engine.dispose()


def test_runtime_database_role_does_not_bypass_rls():
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as connection:
            is_superuser, bypasses_rls = connection.execute(text("""
                SELECT r.rolsuper, r.rolbypassrls
                FROM pg_roles r WHERE r.rolname = current_user
            """)).one()
            assert not is_superuser
            assert not bypasses_rls
    finally:
        engine.dispose()
