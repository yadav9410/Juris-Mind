import json
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401
from app.models.tenant import Tenant, AppUser
from app.models.research import ResearchSnapshot, ResearchSnapshotEvidence
from app.research.orchestrator import run_research


def test_research_run_persists_snapshot_plan_and_frozen_evidence():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    def fake_search(db, query, **kwargs):
        return [{
            "chunk_id": "chunk-1",
            "job_id": "job-1",
            "filename": "sample-judgment.pdf",
            "locator": "Paragraph 12",
            "page_start": 4,
            "page_end": 4,
            "snippet": f"Evidence relevant to {query}",
            "hybrid_score": 0.75,
        }]

    with Session(engine) as db:
        db.add_all([
            Tenant(id="tenant-1", name="Workspace"),
            AppUser(id="user-1", email="user@example.com"),
        ])
        db.commit()

        snapshot = run_research(
            db,
            tenant_id="tenant-1",
            user_id="user-1",
            question="What is the legal test for bail?; How do courts apply it?",
            supplied_sub_questions=["Bail legal test", "Court application"],
            search_fn=fake_search,
        )
        db.commit()

        saved = db.get(ResearchSnapshot, snapshot.id)
        evidence = db.scalars(
            select(ResearchSnapshotEvidence)
            .where(ResearchSnapshotEvidence.snapshot_id == snapshot.id)
            .order_by(ResearchSnapshotEvidence.ordinal)
        ).all()

        assert saved.status == "completed"
        plan = json.loads(saved.plan_json)
        summary = json.loads(saved.summary_json)
        assert plan["sub_questions"] == ["Bail legal test", "Court application"]
        assert summary["query_count"] == 2
        assert summary["result_count"] == 2
        assert len(evidence) == 2
        assert evidence[0].chunk_id == "chunk-1"
        assert json.loads(evidence[0].evidence_json)["locator"] == "Paragraph 12"

    engine.dispose()


def test_empty_search_results_still_create_a_completed_snapshot():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Tenant(id="tenant-1", name="Workspace"),
            AppUser(id="user-1", email="user@example.com"),
        ])
        db.commit()
        snapshot = run_research(
            db,
            tenant_id="tenant-1",
            user_id="user-1",
            question="What is the statutory test for bail?",
            search_fn=lambda *args, **kwargs: [],
        )
        db.commit()
        assert snapshot.status == "completed"
        assert json.loads(snapshot.summary_json)["result_count"] == 0
    engine.dispose()


def test_research_snapshot_includes_external_official_document_evidence():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    def fake_external(query, **kwargs):
        return {
            "external_search_status": "completed",
            "result_count": 1,
            "document_count": 1,
            "verification_status": "not_verified",
            "results": [{
                "source_id": "india_code",
                "source_name": "India Code",
                "title": "Insolvency and Bankruptcy Code, 2016",
                "source_url": "https://www.indiacode.gov.in/example",
                "retrieval_status": "document_retrieved",
                "document_retrieved": True,
                "content_sha256": "abc123",
                "extracted_text": "Section 7 text",
                "page_evidence": [{"page": 1, "text": "Section 7 text"}],
                "verification_status": "not_verified",
            }],
        }

    with Session(engine) as db:
        db.add_all([
            Tenant(id="tenant-1", name="Workspace"),
            AppUser(id="user-1", email="user@example.com"),
        ])
        db.commit()
        snapshot = run_research(
            db, tenant_id="tenant-1", user_id="user-1",
            question="Research IBC Section 7",
            search_fn=lambda *args, **kwargs: [],
            external_search_fn=fake_external,
        )
        db.commit()
        summary = json.loads(snapshot.summary_json)
        evidence = db.scalars(
            select(ResearchSnapshotEvidence)
            .where(ResearchSnapshotEvidence.snapshot_id == snapshot.id)
            .order_by(ResearchSnapshotEvidence.ordinal)
        ).all()
        assert summary["external_search_status"] == "completed"
        assert summary["external_document_count"] == 1
        assert len(evidence) == 1
        fields = json.loads(evidence[0].evidence_json)
        assert fields["source_id"] == "india_code"
        assert fields["verification_status"] == "not_verified"
        assert evidence[0].chunk_id is None
    engine.dispose()
