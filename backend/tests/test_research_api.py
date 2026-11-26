import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
import app.models  # noqa: F401
from app.main import app
from app.db.session import get_db
from app.security.auth import get_current_user
from app.models.tenant import Tenant, AppUser, TenantMembership
from app.models.research import ResearchSnapshot, ResearchSnapshotEvidence


def test_research_snapshot_api_creates_and_reads_workspace_snapshot(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Tenant(id="tenant-1", name="Workspace"),
            AppUser(id="user-1", email="user@example.com"),
        ])
        db.flush()
        db.add(TenantMembership(id="membership-1", tenant_id="tenant-1", user_id="user-1", role="owner"))
        db.commit()

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: {"app_user_id": "user-1"}
    monkeypatch.setattr(
        "app.research.orchestrator.search_legal_chunks_hybrid",
        lambda db, query, **kwargs: [{
            "chunk_id": "chunk-1", "job_id": "job-1", "filename": "act.pdf",
            "locator": "Section 5", "page_start": 2, "page_end": 2,
            "snippet": "Relevant provision", "hybrid_score": 0.5,
        }],
    )

    try:
        client = TestClient(app)
        response = client.post("/research/snapshots", json={
            "tenant_id": "tenant-1",
            "question": "What does Section 5 require?",
            "sub_questions": ["Section 5 requirements"],
        })
        assert response.status_code == 201, response.text
        body = response.json()
        snapshot_id = body["snapshot_id"]
        assert body["status"] == "completed"
        assert body["summary"]["result_count"] == 1

        read = client.get(f"/research/snapshots/{snapshot_id}")
        assert read.status_code == 200, read.text
        assert len(read.json()["evidence"]) == 1

        listed = client.get("/research/snapshots", params={"tenant_id": "tenant-1"})
        assert listed.status_code == 200
        assert listed.json()["count"] == 1
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_viewer_cannot_create_research_snapshot(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Tenant(id="tenant-1", name="Workspace"),
            AppUser(id="user-1", email="user@example.com"),
        ])
        db.flush()
        db.add(TenantMembership(id="membership-1", tenant_id="tenant-1", user_id="user-1", role="viewer"))
        db.commit()

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: {"app_user_id": "user-1"}
    try:
        response = TestClient(app).post("/research/snapshots", json={
            "tenant_id": "tenant-1",
            "question": "What does Section 5 require?",
        })
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
