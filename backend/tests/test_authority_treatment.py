from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.security.auth import get_current_user
from app.api.authority_treatment import router
from app.models.tenant import AppUser, Tenant, TenantMembership
from app.models.ingestion import IngestionJob, IngestionChunk
from app.models.evidence import EvidenceVerification


def _client(role="admin"):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    tenant = Tenant(id="tenant-1", name="Test workspace")
    user = AppUser(id="user-1", email="user@example.test")
    membership = TenantMembership(id="membership-1", tenant_id="tenant-1", user_id="user-1", role=role)
    job = IngestionJob(id="job-treating", filename="later.pdf", content_sha256="a"*64,
                       content_type="application/pdf", status="extracted", storage_key="originals/later.pdf")
    chunk = IngestionChunk(id="chunk-treating", job_id="job-treating", ordinal=1,
                           chunk_type="body", body_text="The Court followed the earlier decision.",
                           page_start=12, page_end=12)
    session.add_all([tenant, user, membership, job, chunk])
    session.commit()

    app = FastAPI()
    app.include_router(router)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: {"app_user_id": "user-1"}
    return TestClient(app), session, engine


def test_create_review_and_read_authority_treatment():
    client, session, engine = _client()
    response = client.post("/research/authority/treatments", json={
        "tenant_id": "tenant-1",
        "subject_citation": "2020 SCC 10",
        "subject_title": "Earlier decision",
        "treatment_type": "followed",
        "treatment_scope": "The later court expressly followed the ratio on the identified issue.",
        "treating_job_id": "job-treating",
        "evidence_chunk_id": "chunk-treating",
        "treating_decision_date": "2026-10-01"
    })
    assert response.status_code == 201, response.text
    treatment_id = response.json()["treatment_id"]
    assert response.json()["review"]["decision"] == "pending"

    review = client.post(f"/research/authority/treatments/{treatment_id}/review", json={
        "decision": "confirmed",
        "note": "Reviewed the cited passage and surrounding context against the ingested judgment."
    })
    assert review.status_code == 201, review.text
    assert review.json()["review"]["decision"] == "confirmed"

    fetched = client.get(f"/research/authority/treatments/{treatment_id}")
    assert fetched.status_code == 200
    assert fetched.json()["treatment"]["type"] == "followed"

    history = client.get("/research/authority/history", params={
        "authority_citation": "2020 SCC 10", "tenant_id": "tenant-1"
    })
    assert history.status_code == 200
    body = history.json()
    assert body["treatment_count"] == 1
    assert body["confirmed_positive_treatment_count"] == 1
    assert body["currentness_assessment"] == "review_required"
    session.close()
    engine.dispose()


def test_invalid_treatment_type_rejected():
    client, session, engine = _client()
    response = client.post("/research/authority/treatments", json={
        "tenant_id": "tenant-1", "subject_citation": "2020 SCC 10",
        "treatment_type": "good_law", "treatment_scope": "Some detailed description.",
        "treating_job_id": "job-treating", "evidence_chunk_id": "chunk-treating"
    })
    assert response.status_code == 422
    session.close()
    engine.dispose()


def test_member_cannot_record_admin_review():
    client, session, engine = _client(role="member")
    response = client.post("/research/authority/treatments", json={
        "tenant_id": "tenant-1", "subject_citation": "2020 SCC 10",
        "treatment_type": "distinguished", "treatment_scope": "The later court distinguished the earlier ratio.",
        "treating_job_id": "job-treating", "evidence_chunk_id": "chunk-treating"
    })
    assert response.status_code == 201
    treatment_id = response.json()["treatment_id"]
    review = client.post(f"/research/authority/treatments/{treatment_id}/review", json={
        "decision": "confirmed", "note": "Review note with sufficient detail."
    })
    assert review.status_code == 403
    session.close()
    engine.dispose()


def test_evidence_chunk_must_belong_to_treating_job():
    client, session, engine = _client()
    response = client.post("/research/authority/treatments", json={
        "tenant_id": "tenant-1", "subject_citation": "2020 SCC 10",
        "treatment_type": "followed", "treatment_scope": "The later court followed the ratio.",
        "treating_job_id": "job-treating", "evidence_chunk_id": "missing-chunk"
    })
    assert response.status_code == 422
    session.close()
    engine.dispose()
