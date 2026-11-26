
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(os.environ["APP_DATABASE_URL"])

subject = "eed51146-db71-4018-828c-d44abb32a3a6"

try:
    with engine.begin() as connection:
        connection.execute(
            text("""
                SELECT set_config(
                    'app.supabase_user_id',
                    :subject,
                    true
                )
            """),
            {"subject": subject},
        )

        result = connection.execute(
            text("""
                SELECT
                    current_user,
                    current_setting(
                        'app.supabase_user_id',
                        true
                    ) AS identity_context,
                    (
                        current_setting(
                            'app.supabase_user_id',
                            true
                        )::uuid = CAST(:subject AS uuid)
                    ) AS identity_matches,
                    (
                        SELECT count(*)
                        FROM public.app_users
                    ) AS visible_accounts
            """),
            {"subject": subject},
        ).mappings().one()

        print(dict(result))

finally:
    engine.dispose()
