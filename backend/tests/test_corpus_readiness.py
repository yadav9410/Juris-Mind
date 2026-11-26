import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401
from app.models.ingestion import IngestionJob, IngestionChunk
from app.research.diagnostics import get_corpus_readiness


def test_corpus_readiness_explains_empty_repository():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        result = get_corpus_readiness(db)
        assert result["total_ingestion_jobs"] == 0
        assert result["searchable_chunks"] == 0
        assert result["search_ready"] is False
        assert "Ingest a PDF or HTML" in result["next_action"]
    engine.dispose()


def test_corpus_readiness_counts_searchable_and_reviewed_documents():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        job = IngestionJob(
            id="job-1",
            filename="act.pdf",
            content_sha256="a" * 64,
            content_type="application/pdf",
            status="extracted",
            metadata_review_status="approved",
            authority_verified=True,
            source_class="primary",
            reviewed_metadata_json=json.dumps({"title": "Example Act"}),
        )
        db.add(job)
        db.flush()
        db.add(IngestionChunk(
            id="chunk-1",
            job_id="job-1",
            ordinal=1,
            chunk_type="provision",
            locator="Section 1",
            heading="Short title",
            body_text="This is a searchable statutory provision.",
            page_start=1,
            page_end=1,
        ))
        db.commit()

        result = get_corpus_readiness(db)
        assert result["total_ingestion_jobs"] == 1
        assert result["searchable_ingestion_jobs"] == 1
        assert result["total_staged_chunks"] == 1
        assert result["searchable_chunks"] == 1
        assert result["reviewed_authority_documents"] == 1
        assert result["search_ready"] is True
        assert result["authority_filtered_search_ready"] is True
    engine.dispose()
