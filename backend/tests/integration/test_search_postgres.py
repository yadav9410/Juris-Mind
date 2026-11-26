"""Optional read-only PostgreSQL search smoke test.

Set TEST_DATABASE_URL to a disposable/test-branch URL using jurismind_app
(after migrations) to execute the real retrieval SQL. This test inserts nothing.
"""
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.search.hybrid import search_legal_chunks_hybrid

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not URL or not URL.startswith(("postgresql://", "postgresql+psycopg://")),
    reason="Set TEST_DATABASE_URL to the jurismind_app connection on the Neon test branch.",
)


def test_postgres_search_query_executes_read_only():
    engine = create_engine(URL, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            current_user = connection.execute(text("SELECT current_user")).scalar_one()
            assert current_user == "jurismind_app", "Use restricted runtime role, not neondb_owner"
            with Session(bind=connection) as session:
                results = search_legal_chunks_hybrid(session, "section 420", limit=5)
                assert isinstance(results, list)
    finally:
        engine.dispose()
