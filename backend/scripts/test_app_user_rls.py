
import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load the project's environment configuration.
load_dotenv()

database_url = os.getenv("APP_DATABASE_URL")

if not database_url:
    raise RuntimeError("APP_DATABASE_URL is missing from .env")

# This is the actual runtime application connection.
engine = create_engine(database_url, pool_pre_ping=True)

# Supabase UUID belonging to the provisioned test account.
supabase_user_id = "eed51146-db71-4018-828c-d44abb32a3a6"

# Validate the UUID before querying.
uuid.UUID(supabase_user_id)

try:
    with engine.begin() as connection:

        # Establish the transaction-local identity used by RLS.
        connection.execute(
            text("""
                SELECT set_config(
                    'app.supabase_user_id',
                    :subject,
                    true
                )
            """),
            {"subject": supabase_user_id},
        )

        # Check the actual PostgreSQL role and identity context.
        context = connection.execute(
            text("""
                SELECT
                    current_database() AS database_name,
                    current_user AS database_role,
                    current_setting(
                        'app.supabase_user_id',
                        true
                    ) AS identity_context
            """)
        ).mappings().one()

        print("\nDATABASE CONTEXT")
        print(dict(context))

        # Perform the same account lookup used by authentication.
        user = connection.execute(
            text("""
                SELECT id, email, supabase_user_id
                FROM public.app_users
                WHERE supabase_user_id = CAST(:subject AS uuid)
            """),
            {"subject": supabase_user_id},
        ).mappings().first()

        print("\nACCOUNT LOOKUP")

        if user:
            print("ACCOUNT FOUND")
            print("Internal user ID:", user["id"])
            print("Workspace email:", user["email"])
        else:
            print("ACCOUNT NOT VISIBLE TO THIS DATABASE ROLE")

finally:
    engine.dispose()
