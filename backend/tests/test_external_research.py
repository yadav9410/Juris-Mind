import pytest

from app.sources.external_research import (
    ExternalSearchNotConfigured, OFFICIAL_DOMAINS, _host_allowed,
    search_official_sources,
)


def test_official_host_allowlist_rejects_non_official_and_http():
    assert _host_allowed("https://indiacode.gov.in/handle/123", "india_code")
    assert not _host_allowed("https://example.com/act.pdf", "india_code")
    assert not _host_allowed("http://indiacode.gov.in/act.pdf", "india_code")
    assert not _host_allowed("https://indiacode.gov.in.evil.example/act.pdf", "india_code")


def test_external_search_requires_provider_key(monkeypatch):
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    with pytest.raises(ExternalSearchNotConfigured):
        search_official_sources("IBC Section 7")


def test_invalid_query_rejected_before_provider_call(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")
    with pytest.raises(ValueError):
        search_official_sources("  ")


def test_source_registry_domains_are_explicit():
    assert "indiacode.gov.in" in OFFICIAL_DOMAINS["india_code"]
    assert "scr.sci.gov.in" in OFFICIAL_DOMAINS["supreme_court_scr"]
    assert "elegalix.allahabadhighcourt.in" in OFFICIAL_DOMAINS["allahabad_elegalix"]


def test_external_search_returns_only_allowlisted_official_results(monkeypatch):
    import os
    import app.sources.external_research as external

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {"web": {"results": [
                {"title": "IBC", "url": "https://indiacode.gov.in/act/ibc", "description": "Official Act"},
                {"title": "Not official", "url": "https://example.com/ibc", "description": "Ignore"},
            ]}}

    monkeypatch.setattr(external.httpx, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(external, "_fetch_official_document", lambda url, sid, timeout=18.0: {
        "source_url": url, "document_retrieved": True,
        "extracted_text": "Section 7", "content_sha256": "hash",
        "retrieval_status": "document_retrieved",
    })
    result = external.search_official_sources(
        "IBC Section 7", categories=["legislation"], max_results_per_source=5,
    )
    assert result["external_search_status"] == "completed"
    assert result["document_count"] == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["source_id"] == "india_code"
    assert result["results"][0]["verification_status"] == "not_verified"
    assert result["downloaded_documents_count"] == 1
    assert result["extracted_documents_count"] == 1
    assert result["verified_authorities_count"] == 0
    assert result["source_summaries"]["india_code"]["downloaded_documents_count"] == 1



def test_source_queries_are_tailored_by_category():
    from app.sources.external_research import _build_source_query

    base = "employment agreement enforceability"
    assert "statutory text" in _build_source_query(base, "india_code", "India", None)
    assert "Insolvency and Bankruptcy Code" not in _build_source_query(base, "india_code", "India", None)
    assert "Gazette notification" in _build_source_query(base, "egazette_india", "India", None)
    assert "judgment" in _build_source_query(base, "supreme_court_scr", "India", None)
    assert "Allahabad High Court" in _build_source_query(base, "allahabad_elegalix", "Uttar Pradesh", "Allahabad High Court")


def test_result_accounting_separates_download_and_extraction(monkeypatch):
    import app.sources.external_research as external

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return {"web": {"results": [
                {"title": "IBC PDF", "url": "https://indiacode.gov.in/act/ibc.pdf", "description": "Act"},
                {"title": "IBC page", "url": "https://indiacode.gov.in/act/ibc", "description": "Page"},
            ]}}

    monkeypatch.setattr(external.httpx, "get", lambda *args, **kwargs: FakeResponse())
    def fake_fetch(url, sid, timeout=18.0):
        if url.endswith(".pdf"):
            return {"downloaded": True, "extracted": False, "document_retrieved": False,
                    "content_sha256": "hash-a", "extracted_text": ""}
        return {"downloaded": True, "extracted": True, "document_retrieved": True,
                "content_sha256": "hash-b", "extracted_text": "Section 7"}
    monkeypatch.setattr(external, "_fetch_official_document", fake_fetch)

    result = external.search_official_sources("IBC Section 7", categories=["legislation"])
    assert result["search_results_count"] == 2
    assert result["downloaded_documents_count"] == 2
    assert result["extracted_documents_count"] == 1
    assert result["verified_authorities_count"] == 0
    assert result["failed_retrievals_count"] == 0
    assert result["document_count"] == 2


def test_failed_document_retrieval_is_counted(monkeypatch):
    import httpx
    import app.sources.external_research as external

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return {"web": {"results": [
                {"title": "Gazette notice", "url": "https://egazette.gov.in/notice/1", "description": "Notice"},
            ]}}

    monkeypatch.setattr(external.httpx, "get", lambda *args, **kwargs: FakeResponse())
    request = httpx.Request("GET", "https://egazette.gov.in/notice/1")
    response = httpx.Response(429, request=request, headers={"Retry-After": "30"})
    def fail_fetch(url, sid, timeout=18.0):
        raise httpx.HTTPStatusError("429 Too Many Requests", request=request, response=response)
    monkeypatch.setattr(external, "_fetch_official_document", fail_fetch)

    result = external.search_official_sources("Gazette IBC amendment", categories=["gazette"])
    assert result["search_results_count"] == 1
    assert result["downloaded_documents_count"] == 0
    assert result["extracted_documents_count"] == 0
    assert result["failed_retrievals_count"] == 1
    assert result["results"][0]["retrieval_error_type"] == "HTTPStatusError"
    assert result["results"][0]["http_status"] == 429
