"""Read-only checks for the Neon test branch search setup.

Uses TEST_DATABASE_URL (migration/admin role) to inspect migration/index state,
then APP_DATABASE_URL (jurismind_app role) to execute the real search query.
No rows are inserted, updated, or deleted.
"""
from __future__ import annotations
import os
import sys
from dotenv import load_dotenv

# Load environment variables from the project's .env file.
load_dotenv()
from sqlalchemy import create_engine, text
from app.search.hybrid import search_legal_chunks_hybrid


def main() -> int:
    admin_url = os.getenv("DATABASE_URL")
    app_url = os.getenv("APP_DATABASE_URL")
    if not admin_url or not app_url:
        print("Set DATABASE_URL (neondb_owner on the test branch) and APP_DATABASE_URL (jurismind_app on the same branch).")
        return 2

    admin = create_engine(admin_url, pool_pre_ping=True)
    runtime = create_engine(app_url, pool_pre_ping=True)
    try:
        with admin.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            index_exists = conn.execute(text("SELECT to_regclass('public.ix_ingestion_chunks_fts') IS NOT NULL")).scalar_one()
            print(f"Migration version: {version}")
            print(f"Full-text GIN index exists: {index_exists}")
            read_grants = conn.execute(text("""
                SELECT
                    has_table_privilege('jurismind_app', 'ingestion_jobs', 'SELECT')
                    AND has_table_privilege('jurismind_app', 'ingestion_chunks', 'SELECT')
                    AS can_read,
                    has_table_privilege('jurismind_app', 'ingestion_jobs', 'INSERT')
                    OR has_table_privilege('jurismind_app', 'ingestion_jobs', 'UPDATE')
                    OR has_table_privilege('jurismind_app', 'ingestion_jobs', 'DELETE')
                    OR has_table_privilege('jurismind_app', 'ingestion_chunks', 'INSERT')
                    OR has_table_privilege('jurismind_app', 'ingestion_chunks', 'UPDATE')
                    OR has_table_privilege('jurismind_app', 'ingestion_chunks', 'DELETE')
                    AS can_write
            """)).one()
            print(f"Runtime SELECT grants present: {read_grants.can_read}")
            print(f"Runtime write grants present (should be False): {read_grants.can_write}")
            if version != "0009_search_runtime_read_access":
                print("WARNING: expected migration 0009_search_runtime_read_access; apply pending migrations on this TEST branch.")
            if not index_exists:
                print("WARNING: migration 0007 full-text index is not present.")

        with runtime.connect() as conn:
            user, database = conn.execute(text("SELECT current_user, current_database()")).one()
            print(f"Runtime connection: {user} @ {database}")
            if user != "jurismind_app":
                print("WARNING: APP_DATABASE_URL is not using jurismind_app.")
            # Execute the same parameterized retrieval SQL used by the API.
            from sqlalchemy.orm import Session
            with Session(bind=conn) as session:
                hits = search_legal_chunks_hybrid(session, "section 420", limit=5)
                print(f"Search SQL executed successfully; matching passages: {len(hits)}")
        return 0
    except Exception as exc:
        print(f"Search database validation failed: {type(exc).__name__}: {exc}")
        return 1
    finally:
        runtime.dispose()
        admin.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
