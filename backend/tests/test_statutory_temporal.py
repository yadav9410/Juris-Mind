from datetime import date
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.security.auth import get_current_user
from app.api.statutory import router
from app.models.tenant import AppUser, Tenant, TenantMembership
from app.models.ingestion import IngestionJob, IngestionChunk


def _client(role="owner"):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add_all([
        Tenant(id="tenant-1", name="Workspace"),
        AppUser(id="user-1", email="user@example.test"),
        TenantMembership(id="membership-1", tenant_id="tenant-1", user_id="user-1", role=role),
        IngestionJob(id="job-1", filename="act.pdf", content_sha256="a"*64,
                     content_type="application/pdf", status="extracted", storage_key="originals/act.pdf"),
        IngestionChunk(id="chunk-1", job_id="job-1", ordinal=1, chunk_type="provision",
                       body_text="The text of section 1 as published.", page_start=1, page_end=1),
    ])
    session.commit()
    app = FastAPI()
    app.include_router(router)
    def override_db():
        yield session
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: {"app_user_id": "user-1"}
    return TestClient(app), session, engine


def test_create_instrument_provision_version_and_as_of_lookup():
    client, session, engine = _client()
    instrument = client.post("/research/statutes/instruments", json={
        "title": "Illustrative Act, 2020", "canonical_identifier": "Illustrative Act 2020",
        "instrument_type": "central_act", "jurisdiction": "India",
        "enactment_date": "2020-03-01", "publication_date": "2020-03-05"
    })
    assert instrument.status_code == 201, instrument.text
    iid = instrument.json()["instrument_id"]

    provision = client.post(f"/research/statutes/instruments/{iid}/provisions", json={
        "provision_ref": "Section 1", "heading": "Short title"
    })
    assert provision.status_code == 201, provision.text
    pid = provision.json()["provision_id"]

    version = client.post(f"/research/statutes/provisions/{pid}/versions", json={
        "version_label": "Original",
        "text": "This Act may be called the Illustrative Act, 2020.",
        "effective_from": "2020-03-05",
        "effective_to": "2022-01-01",
        "commencement_date": "2020-03-05",
        "publication_date": "2020-03-05",
        "source_job_id": "job-1", "source_chunk_id": "chunk-1"
    })
    assert version.status_code == 201, version.text
    lookup = client.get(f"/research/statutes/provisions/{pid}/as-of", params={"date": "2021-06-01"})
    assert lookup.status_code == 200, lookup.text
    assert lookup.json()["historical_status"] == "partial"
    assert lookup.json()["applicable_version"]["version_label"] == "Original"

    outside = client.get(f"/research/statutes/provisions/{pid}/as-of", params={"date": "2023-01-01"})
    assert outside.status_code == 200
    assert outside.json()["historical_status"] == "unresolved"
    session.close()
    engine.dispose()


def test_overlapping_effective_period_is_rejected():
    client, session, engine = _client()
    instrument = client.post("/research/statutes/instruments", json={
        "title": "Illustrative Act", "canonical_identifier": "Act-Overlap",
        "instrument_type": "act"
    }).json()
    provision = client.post(f"/research/statutes/instruments/{instrument['instrument_id']}/provisions",
                            json={"provision_ref": "Section 2"}).json()
    url = f"/research/statutes/provisions/{provision['provision_id']}/versions"
    base = {"text": "Original text", "effective_from": "2020-01-01",
            "effective_to": "2022-01-01", "source_job_id": "job-1", "source_chunk_id": "chunk-1"}
    first = client.post(url, json=base)
    assert first.status_code == 201, first.text
    second = client.post(url, json={**base, "effective_from": "2021-01-01"})
    assert second.status_code == 409
    session.close()
    engine.dispose()


def test_member_cannot_write_shared_statutory_corpus():
    client, session, engine = _client(role="member")
    response = client.post("/research/statutes/instruments", json={
        "title": "Restricted Act", "canonical_identifier": "Restricted-Act",
        "instrument_type": "act"
    })
    assert response.status_code == 403
    session.close()
    engine.dispose()


def test_version_requires_source_chunk_from_supplied_job():
    client, session, engine = _client()
    instrument = client.post("/research/statutes/instruments", json={
        "title": "Source Act", "canonical_identifier": "Source-Act", "instrument_type": "act"
    }).json()
    provision = client.post(f"/research/statutes/instruments/{instrument['instrument_id']}/provisions",
                            json={"provision_ref": "Section 3"}).json()
    response = client.post(f"/research/statutes/provisions/{provision['provision_id']}/versions", json={
        "text": "Text", "effective_from": "2020-01-01",
        "source_job_id": "job-1", "source_chunk_id": "not-the-chunk"
    })
    assert response.status_code == 422
    session.close()
    engine.dispose()


def test_close_version_preserves_text_and_sets_exclusive_end_date():
    client, session, engine = _client()
    instrument = client.post("/research/statutes/instruments", json={
        "title": "Close Act", "canonical_identifier": "Close-Act", "instrument_type": "act"
    }).json()
    provision = client.post(f"/research/statutes/instruments/{instrument['instrument_id']}/provisions",
                            json={"provision_ref": "Section 4"}).json()
    version = client.post(f"/research/statutes/provisions/{provision['provision_id']}/versions", json={
        "text": "Preserved original wording", "effective_from": "2020-01-01",
        "source_job_id": "job-1", "source_chunk_id": "chunk-1"
    }).json()
    closed = client.post(f"/research/statutes/versions/{version['version_id']}/close",
                         json={"effective_to": "2022-01-01"})
    assert closed.status_code == 200, closed.text
    assert closed.json()["effective_to"] == "2022-01-01"
    session.close()
    engine.dispose()
