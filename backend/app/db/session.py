"""Runtime application database engine and request-scoped sessions.

Alembic continues to use DATABASE_URL (the migration/admin connection).
The API uses APP_DATABASE_URL so runtime requests never need the owner role.
"""
import warnings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()
_runtime_url = settings.app_database_url
if not _runtime_url:
    if settings.database_url.startswith("sqlite"):
        # Local development/tests may share the SQLite development database.
        _runtime_url = settings.database_url
    else:
        raise RuntimeError(
            "APP_DATABASE_URL is required for PostgreSQL runtime access. "
            "Configure it with the jurismind_app role; DATABASE_URL is reserved for migrations."
        )

_connect_args = {"check_same_thread": False} if _runtime_url.startswith("sqlite") else {}
engine = create_engine(_runtime_url, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    """Yield one SQLAlchemy session per request and always close it."""
    session = SessionLocal()
    try:
        yield session
    finally:
        # Closing rolls back any uncommitted transaction and clears SET LOCAL state.
        session.close()
