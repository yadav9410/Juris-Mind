"""API contract tests for authenticated hybrid legal search."""
from fastapi.testclient import TestClient
from app.main import app
from app.security.auth import get_current_user
from app.api.search import search_legal_chunks_hybrid


def test_hybrid_search_requires_authentication():
    response = TestClient(app).get("/search/hybrid", params={"q": "section 420"})
    assert response.status_code == 401


def test_hybrid_search_returns_discovery_notice_and_metadata(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "00000000-0000-0000-0000-000000000001",
        "app_user_id": "test-user",
    }
    monkeypatch.setattr(
        "app.api.search.search_legal_chunks_hybrid",
        lambda db, query, **kwargs: [{
            "chunk_id": "chunk-1", "filename": "sample-act.pdf",
            "locator": "Section 420", "page_start": None,
            "page_end": None, "snippet": "sample passage",
        }],
    )
    try:
        response = TestClient(app).get(
            "/search/hybrid",
            params={"q": "section 420", "document_type": "act", "limit": 5},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["locator"] == "Section 420"
    assert body["semantic_vectors_enabled"] is False
    assert "verify the original source" in body["notice"]


def test_hybrid_search_rejects_missing_query():
    app.dependency_overrides[get_current_user] = lambda: {"app_user_id": "test-user"}
    try:
        response = TestClient(app).get("/search/hybrid")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
