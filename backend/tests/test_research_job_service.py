from app.research import job_service


class FakeJob:
    def __init__(self):
        self.id = "job-123"
        self.status = "queued"
        self.stage = "queued"
        self.started_at = None
        self.attempts = 0


class FakeSession:
    def __init__(self, job):
        self.job = job
        self.committed = False
    def scalar(self, statement):
        return self.job
    def commit(self):
        self.committed = True


def test_claim_next_job_returns_stable_id_not_detached_orm_object():
    job = FakeJob()
    db = FakeSession(job)
    result = job_service.claim_next_job(db)
    assert result == "job-123"
    assert isinstance(result, str)
    assert db.committed is True
    assert job.status == "running"
    assert job.stage == "researching"
    assert job.attempts == 1


def test_execute_job_searches_without_candidate_document_type_filter(monkeypatch):
    import json
    from contextlib import contextmanager
    from datetime import datetime, timezone

    job = FakeJob()
    job.status = "running"
    job.question = "What is a valid contract under Section 10?"
    job.jurisdiction = "India"
    job.court = None
    job.legislation_status = "queued"
    job.case_law_status = "queued"
    job.progress = 0
    job.result_json = "{}"
    job.completed_at = None
    job.error_message = None

    class JobSession(FakeSession):
        def get(self, model, job_id):
            return job if job_id == job.id else None

    @contextmanager
    def factory():
        yield JobSession(job)

    calls = []
    def fake_search(db, query, **kwargs):
        calls.append(kwargs)
        return [{
            "chunk_id": "chunk-1",
            "effective_document_type": "order",
            "filename": "IBC_2016_Original_Gazette.pdf",
            "snippet": "Section 10 legal passage",
        }]

    monkeypatch.setattr(job_service, "search_legal_chunks_hybrid", fake_search)
    job_service.execute_job(factory, "job-123")

    assert len(calls) == 1
    assert calls[0]["document_type"] is None
    payload = json.loads(job.result_json)
    assert payload["retrieved"][0]["chunk_id"] == "chunk-1"
    assert payload["other_evidence"][0]["effective_document_type"] == "order"
    assert job.status == "completed"
