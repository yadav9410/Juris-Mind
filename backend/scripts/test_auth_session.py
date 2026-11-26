
from sqlalchemy import text, select

from app.db.session import SessionLocal
from app.models.tenant import AppUser

SUPABASE_USER_ID = "eed51146-db71-4018-828c-d44abb32a3a6"

db = SessionLocal()

try:
    # Set the same transaction-local identity used by get_current_user().
    db.execute(
        text("""
            SELECT set_config(
                'app.supabase_user_id',
                :subject,
                true
            )
        """),
        {"subject": SUPABASE_USER_ID},
    )

    # Inspect the actual session and transaction context.
    context = db.execute(
        text("""
            SELECT
                current_database() AS database_name,
                current_user AS database_role,
                current_setting(
                    'app.supabase_user_id',
                    true
                ) AS identity_context,
                current_schema() AS current_schema,
                to_regclass('app_users') AS resolved_table,
                to_regclass('public.app_users') AS public_table
        """)
    ).mappings().one()

    print("\nSESSION CONTEXT")
    print(dict(context))

    # Run the raw SQL lookup through this exact SessionLocal session.
    raw_user = db.execute(
        text("""
            SELECT id, email, supabase_user_id
            FROM public.app_users
            WHERE supabase_user_id = CAST(:subject AS uuid)
        """),
        {"subject": SUPABASE_USER_ID},
    ).mappings().first()

    print("\nRAW SQL LOOKUP")
    print(dict(raw_user) if raw_user else "ACCOUNT NOT FOUND")

    # Run the same ORM lookup used by get_current_user().
    orm_user = db.scalar(
        select(AppUser).where(
            AppUser.supabase_user_id
            == __import__("uuid").UUID(SUPABASE_USER_ID)
        )
    )

    print("\nORM LOOKUP")
    if orm_user:
        print("ACCOUNT FOUND")
        print("Internal user ID:", orm_user.id)
        print("Email:", orm_user.email)
    else:
        print("ACCOUNT NOT FOUND")

finally:
    db.close()
