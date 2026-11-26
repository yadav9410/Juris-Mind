
"""JurisMind API application entry point."""

import logging
import os
from contextlib import asynccontextmanager
from threading import Event, Thread

from fastapi import FastAPI
from sqlalchemy import text

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.tenant import router as tenant_router
from app.api.search import router as search_router
from app.api.ingestion import router as ingestion_router
from app.api.metadata_review import router as metadata_review_router
from app.api.citations import router as citations_router
from app.api.research import router as research_router
from app.api.agents import router as agents_router
from app.api.claim_evidence import router as claim_evidence_router
from app.api.evidence_provenance import router as evidence_provenance_router
from app.api.authority_treatment import router as authority_treatment_router
from app.api.statutory import router as statutory_router
from app.api.judgment_intelligence import router as judgment_intelligence_router
from app.api.reasoning import router as reasoning_router
from app.api.due_diligence import router as due_diligence_router
from app.api.drafting import router as drafting_router
from app.api.platform import router as platform_router
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def research_worker_loop(stop_event: Event):
    from app.db.session import SessionLocal
    from app.research.job_service import claim_next_job, execute_job

    # Temporary diagnostic: identify the worker's actual DB connection.
    try:
        with SessionLocal() as db:
            identity = db.execute(
                text("SELECT current_database(), current_user")
            ).one()

            logger.info(
                "Research worker DB identity: database=%s user=%s",
                identity[0],
                identity[1],
            )
    except Exception:
        logger.exception("Research worker database identity check failed")

    while not stop_event.is_set():
        try:
            with SessionLocal() as db:
                job = claim_next_job(db)
                job_id = job.id if job else None

            if job_id:
                execute_job(SessionLocal, job_id)
            else:
                stop_event.wait(2)

        except Exception:
            logger.exception("Research worker error")
            stop_event.wait(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = Event()
    worker_thread = None

    if os.getenv("RUN_RESEARCH_WORKER", "false").lower() == "true":
        worker_thread = Thread(
            target=research_worker_loop,
            args=(stop_event,),
            name="jurismind-research-worker",
            daemon=True,
        )
        worker_thread.start()
        logger.info("Research worker started")

    yield

    if worker_thread:
        stop_event.set()
        worker_thread.join(timeout=10)
        logger.info("Research worker stopped")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Foundation API for the JurisMind legal intelligence platform.",
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(tenant_router)
app.include_router(search_router)
app.include_router(ingestion_router)
app.include_router(metadata_review_router)
app.include_router(citations_router)
app.include_router(research_router)
app.include_router(agents_router)
app.include_router(claim_evidence_router)
app.include_router(evidence_provenance_router)
app.include_router(authority_treatment_router)
app.include_router(statutory_router)
app.include_router(judgment_intelligence_router)
app.include_router(reasoning_router)
app.include_router(due_diligence_router)
app.include_router(drafting_router)
app.include_router(platform_router)


@app.get("/")
def root():
    """Give developers a small welcome response at the API root."""
    return {"message": "JurisMind API is running", "docs": "/docs"}
