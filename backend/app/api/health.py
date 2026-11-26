"""Simple endpoints used to check whether the API and database are available."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def liveness_check():
    """Return success when the API process is running."""
    return {"status": "alive", "service": "jurismind-api"}


@router.get("/health/ready")
def readiness_check(database: Session = Depends(get_db)):
    """Check that the API can also execute a simple database query."""
    try:
        database.execute(text("SELECT 1"))
    except Exception as error:
        # Do not expose database credentials or raw connection details to clients.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        ) from error

    return {"status": "ready", "database": "connected"}
