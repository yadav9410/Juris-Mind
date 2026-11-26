
"""Check snapshot table permissions using the actual API database connection."""

from sqlalchemy import text
from app.db.session import SessionLocal


def main():
    db = SessionLocal()

    try:
        result = db.execute(text("""
            SELECT
                current_database() AS database_name,
                current_user AS database_role,
                current_schema() AS current_schema,
                current_setting('search_path') AS search_path,
                to_regclass('public.research_snapshots')::text
                    AS snapshot_table,
                has_table_privilege(
                    current_user,
                    'public.research_snapshots',
                    'SELECT'
                ) AS can_select,
                has_table_privilege(
                    current_user,
                    'public.research_snapshots',
                    'INSERT'
                ) AS can_insert,
                has_table_privilege(
                    current_user,
                    'public.research_snapshot_evidence',
                    'SELECT'
                ) AS evidence_can_select,
                has_table_privilege(
                    current_user,
                    'public.research_snapshot_evidence',
                    'INSERT'
                ) AS evidence_can_insert
        """))

        print("\nSNAPSHOT PERMISSION CHECK")
        for key, value in result.mappings().one().items():
            print(f"{key}: {value}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
