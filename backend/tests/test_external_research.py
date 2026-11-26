import pytest

from app.sources.external_research import (
    ExternalSearchNotConfigured, OFFICIAL_DOMAINS, _host_allowed,
    search_official_sources,
)


def test_official_host_allowlist_rejects_non_official_and_http():
    assert _host_allowed("https://indiacode.gov.in/handle/123", "india_code")
    assert _host_allowed("https://upload.indiacode.nic.in/showfile?actid=123&filename=act.pdf", "india_code")
    assert _host_allowed("https://www.indiacode.nic.in/bitstream/123/456/act.pdf", "india_code")
    assert _host_allowed("https://indiacode.nic.in/bitstream/123/456/act.pdf", "india_code")
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
    assert "upload.indiacode.nic.in" in OFFICIAL_DOMAINS["india_code"]
    assert "www.indiacode.nic.in" in OFFICIAL_DOMAINS["india_code"]
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



def test_ssl_context_keeps_certificate_and_hostname_verification_enabled():
    import ssl
    from app.sources.external_research import _ssl_context

    context = _ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_429_activates_host_cooldown_and_suppresses_followup(monkeypatch):
    import time
    import httpx
    from app.sources.external_research import (
        OfficialSourceCooldown, _host_cooldown_until, _host_pacing, _set_host_cooldown,
    )

    host = "elegalix.allahabadhighcourt.in"
    _host_cooldown_until.pop(host, None)
    request = httpx.Request("GET", f"https://{host}/judgment")
    response = httpx.Response(429, request=request, headers={"Retry-After": "120"})
    delay = _set_host_cooldown(host, response)

    assert 119 <= delay <= 120
    with pytest.raises(OfficialSourceCooldown) as exc:
        _host_pacing(host)
    assert exc.value.http_status == 429
    assert exc.value.retry_after_seconds > 0


def test_429_without_retry_after_uses_conservative_default_cooldown():
    import httpx
    from app.sources.external_research import _set_host_cooldown, _host_cooldown_until

    host = "elegalix.allahabadhighcourt.in"
    _host_cooldown_until.pop(host, None)
    request = httpx.Request("GET", f"https://{host}/judgment")
    response = httpx.Response(429, request=request)
    delay = _set_host_cooldown(host, response)
    assert delay == 900.0


def test_nyaykosh_client_reads_documented_law_and_penalty_endpoints():
    import httpx
    from app.sources.nyaykosh import NyaykoshClient

    def handler(request):
        if request.url.path.endswith("/penalties"):
            return httpx.Response(200, json=[{"breach": "Example breach", "section": "S. 9"}],
                                  headers={"content-type": "application/json"})
        return httpx.Response(200, json={"id": "dpdp-2023", "title": "Digital Personal Data Protection Act", "sections": 44},
                              headers={"content-type": "application/json"})

    client = NyaykoshClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = client.get_law_with_penalties("dpdp-2023")
    assert result["law"]["data"]["id"] == "dpdp-2023"
    assert result["law"]["data"]["sections"] == 44
    assert result["penalties"]["status"] == "retrieved"
    assert result["penalties"]["data"][0]["section"] == "S. 9"
    assert result["verification_status"] == "not_independently_verified"


def test_nyaykosh_rejects_invalid_slug_and_non_https_base_url():
    import pytest
    from app.sources.nyaykosh import NyaykoshClient

    with pytest.raises(ValueError):
        NyaykoshClient(base_url="http://lawascode.negd.in/")
    with pytest.raises(ValueError):
        NyaykoshClient().get_law("../dpdp-2023")


def test_nyaykosh_404_is_reported_as_not_found():
    import httpx
    import pytest
    from app.sources.nyaykosh import NyaykoshClient, NyaykoshNotFound

    client = NyaykoshClient(client=httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(404, request=request)
    )))
    with pytest.raises(NyaykoshNotFound):
        client.get_law("ibc-2016")


def test_long_memo_prompt_becomes_short_issue_specific_brave_query():
    from app.sources.external_research import _build_source_query

    prompt = (
        "Research IBC 2016 Section 7 under Indian Central law. Use India Code as the primary "
        "statutory source and NyayKosh as supplementary. Identify amendments, filing requirements, "
        "limitation rules, and key Supreme Court and Allahabad High Court judgments. Prefer official "
        "court documents. Provide case citations, dates, relevant paragraphs, source links and "
        "verification status. Highlight missing evidence and research limitations."
    )
    q = _build_source_query(prompt, "india_code", "India", None)
    assert len(q) <= 220
    assert "IBC" in q
    assert "Section 7" in q
    assert "verification status" not in q.lower()


def test_brave_422_is_reported_as_provider_bad_request(monkeypatch):
    import httpx
    import app.sources.external_research as external

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")
    request = httpx.Request("GET", "https://api.search.brave.com/res/v1/web/search")
    response = httpx.Response(422, request=request, text="Invalid query parameter")

    def fake_get(*args, **kwargs):
        assert len(kwargs["params"]["q"]) <= 300
        return response

    monkeypatch.setattr(external.httpx, "get", fake_get)
    result = external.search_official_sources(
        "Research IBC 2016 Section 7. Use official sources and provide a detailed memo with citations.",
        categories=["legislation"],
    )
    assert result["external_search_status"] == "provider_error"
    assert result["source_errors"][0]["failure_category"] == "provider_bad_request"
    assert result["source_errors"][0]["http_status"] == 422
    assert result["source_summaries"]["india_code"]["search_status"] == "failed"


def test_mixed_provider_success_and_failure_is_partial(monkeypatch):
    import httpx
    import app.sources.external_research as external

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")

    def fake_get(url, params=None, headers=None, timeout=None):
        if "indiacode.gov.in" in params["q"]:
            class Good:
                status_code = 200
                def raise_for_status(self): pass
                def json(self):
                    return {"web": {"results": [{
                        "title": "IBC", "url": "https://indiacode.gov.in/act/ibc", "description": "Act text"
                    }]}}
            return Good()
        request = httpx.Request("GET", url)
        return httpx.Response(422, request=request, text="Bad query")

    monkeypatch.setattr(external.httpx, "get", fake_get)
    monkeypatch.setattr(external, "_fetch_official_document", lambda url, sid, timeout=18.0: {
        "source_url": url, "downloaded": True, "extracted": True,
        "extracted_text": "Section 7", "content_sha256": "abc",
        "verification_status": "not_verified",
    })
    result = external.search_official_sources(
        "IBC 2016 Section 7", categories=["legislation", "gazette"]
    )
    assert result["external_search_status"] == "partial"
    assert result["source_summaries"]["india_code"]["search_status"] == "completed"
    assert result["source_summaries"]["egazette_india"]["search_status"] == "failed"


def test_india_code_viewer_shell_fetches_embedded_pdf_and_uses_its_text(monkeypatch):
    import httpx
    import app.sources.external_research as external

    landing_url = "https://indiacode.gov.in/handle/123456789/1362"
    pdf_url = "https://indiacode.gov.in/bitstream/123456789/1362/1/IBC_2016.pdf"
    html = f'''<html><head><title>Act details</title></head><body>
      <div id="viewer">1</div><iframe src="{pdf_url}"></iframe></body></html>'''
    pdf_bytes = b"%PDF-1.7 fake-for-test"

    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url):
            if url == landing_url:
                return httpx.Response(200, request=httpx.Request("GET", url),
                    headers={"content-type": "text/html"}, text=html)
            assert url == pdf_url
            return httpx.Response(200, request=httpx.Request("GET", url),
                headers={"content-type": "application/pdf"}, content=pdf_bytes)

    monkeypatch.setattr(external.httpx, "Client", FakeClient)
    monkeypatch.setattr(external, "_host_pacing", lambda host: None)
    monkeypatch.setattr(external, "_extract_pdf", lambda content: (
        "THE INSOLVENCY AND BANKRUPTCY CODE, 2016 Section 7. (1) A financial creditor... " * 8,
        [{"page": 1, "text": "Section 7"}], False,
    ))
    external._fetch_cache.clear()

    result = external._fetch_official_document(landing_url, "india_code")
    assert result["downloaded"] is True
    assert result["extracted"] is True
    assert result["access_method"] == "official_landing_page_embedded_document"
    assert result["landing_page_url"] == landing_url
    assert result["source_url"] == pdf_url
    assert "Section 7" in result["extracted_text"]


def test_india_code_pdf_with_only_page_number_is_not_counted_as_extracted(monkeypatch):
    import httpx
    import app.sources.external_research as external

    url = "https://indiacode.gov.in/bitstream/123456789/1362/1/IBC_2016.pdf"

    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, requested_url):
            return httpx.Response(200, request=httpx.Request("GET", requested_url),
                headers={"content-type": "application/pdf"}, content=b"%PDF-1.7 fake")

    monkeypatch.setattr(external.httpx, "Client", FakeClient)
    monkeypatch.setattr(external, "_host_pacing", lambda host: None)
    monkeypatch.setattr(external, "_extract_pdf", lambda content: ("1", [], False))
    external._fetch_cache.clear()

    result = external._fetch_official_document(url, "india_code")
    assert result["downloaded"] is True
    assert result["extracted"] is False
    assert result["extraction_quality"] == "insufficient_text"
    assert result["extracted_text"] == ""
    assert "OCR" in result["extraction_error"]


def test_targeted_section_extraction_preserves_section_and_subsections():
    from app.sources.external_research import _extract_targeted_statutory_provisions

    text = (
        "THE INSOLVENCY AND BANKRUPTCY CODE, 2016\n"
        "7. Initiation of corporate insolvency resolution process by financial creditor.—"
        "(1) A financial creditor either by itself or jointly with other financial creditors, "
        "may file an application for initiating corporate insolvency resolution process "
        "against a corporate debtor before the Adjudicating Authority when a default has occurred.\n"
        "(2) The financial creditor shall make an application under sub-section (1) in such form "
        "and manner and accompanied with such fee as may be prescribed.\n"
        "8. Insolvency resolution by operational creditor.—A creditor may deliver a demand notice."
    )
    result = _extract_targeted_statutory_provisions(text, "Research IBC Section 7")
    assert "7" in result
    assert "(1) A financial creditor" in result["7"]
    assert "(2) The financial creditor" in result["7"]
    assert "8. Insolvency resolution" not in result["7"]


def test_india_code_prefers_embedded_pdf_even_when_landing_page_has_substantial_boilerplate(monkeypatch):
    import httpx
    import app.sources.external_research as external

    landing_url = "https://indiacode.gov.in/handle/123456789/2154"
    pdf_url = "https://upload.indiacode.nic.in/showfile?actid=IBC&filename=a2016-31.pdf&type=actfile"
    html = f"""<html><body><nav>India Code legislation rules regulations notifications statutes</nav>
      <main><h1>The Insolvency and Bankruptcy Code, 2016</h1>
      <p>Act details and related metadata. This page includes enough words to pass a generic
      HTML text threshold but it is not the actual statutory document.</p>
      <a href="{pdf_url}">Download Act PDF</a></main></body></html>"""

    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url):
            if url == landing_url:
                return httpx.Response(200, request=httpx.Request("GET", url),
                    headers={"content-type": "text/html"}, text=html)
            assert url == pdf_url
            return httpx.Response(200, request=httpx.Request("GET", url),
                headers={"content-type": "application/pdf"}, content=b"%PDF-1.7 fake")

    monkeypatch.setattr(external.httpx, "Client", FakeClient)
    monkeypatch.setattr(external, "_host_pacing", lambda host: None)
    monkeypatch.setattr(external, "_extract_pdf", lambda content: (
        "THE INSOLVENCY AND BANKRUPTCY CODE, 2016\n7. Initiation of corporate insolvency resolution process by financial creditor.\n(1) A financial creditor may file an application before the Adjudicating Authority.\n" * 5,
        [{"page": 1, "text": "Section 7 statutory text"}], False,
    ))
    external._fetch_cache.clear()

    result = external._fetch_official_document(landing_url, "india_code")
    assert result["extracted"] is True
    assert result["source_url"] == pdf_url
    assert result["landing_page_url"] == landing_url
    assert result["access_method"] == "official_landing_page_embedded_document"
    assert "financial creditor" in result["extracted_text"]


def test_india_code_showfile_link_is_detected_from_filename_query_parameter():
    from bs4 import BeautifulSoup
    from app.sources.external_research import _html_document_candidates

    html = '''<html><body><a href="https://upload.indiacode.nic.in/showfile?actid=123&filename=a2016-31.pdf&type=actfile">View</a></body></html>'''
    soup = BeautifulSoup(html, "html.parser")
    found = _html_document_candidates(soup, "https://indiacode.gov.in/handle/123", "india_code")
    assert found == ["https://upload.indiacode.nic.in/showfile?actid=123&filename=a2016-31.pdf&type=actfile"]


def test_india_code_direct_legacy_pdf_is_ranked_before_upload_viewer():
    from app.sources.external_research import _rank_official_hits

    hits = [
        {"url": "https://upload.indiacode.nic.in/showfile?actid=123&filename=act.pdf"},
        {"url": "https://www.indiacode.nic.in/bitstream/123/456/A2016-31.pdf"},
        {"url": "https://www.indiacode.gov.in/handle/123"},
    ]
    ranked = _rank_official_hits(hits, "india_code")
    assert ranked[0]["url"].startswith("https://www.indiacode.nic.in/bitstream/")


def test_india_code_search_limits_auto_fetches_but_keeps_all_search_leads(monkeypatch):
    import app.sources.external_research as external

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")
    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return {"web": {"results": [
                {"title": f"IBC {i}", "url": f"https://www.indiacode.nic.in/bitstream/123/{i}/act{i}.pdf", "description": "Act"}
                for i in range(4)
            ]}}

    calls = []
    monkeypatch.setattr(external.httpx, "get", lambda *args, **kwargs: FakeResponse())
    def fake_fetch(url, sid, timeout=18.0):
        calls.append(url)
        return {"downloaded": True, "extracted": True, "document_retrieved": True,
                "content_sha256": "hash", "extracted_text": "Section 7 text"}
    monkeypatch.setattr(external, "_fetch_official_document", fake_fetch)

    result = external.search_official_sources("IBC Section 7", categories=["legislation"], max_results_per_source=4)
    assert len(result["results"]) == 4
    assert len(calls) == 2
    assert sum(r["retrieval_status"] == "search_result_only" for r in result["results"]) == 2


def test_legacy_india_code_pdf_update_date_is_not_mislabeled_current():
    from app.sources.external_research import _detect_source_update_date

    date, status = _detect_source_update_date("THE INSOLVENCY AND BANKRUPTCY CODE, 2016\nLast Update 18-8-2021")
    assert date == "2021-08-18"
    assert status == "currentness_not_established"


def test_undated_source_does_not_claim_currentness():
    from app.sources.external_research import _detect_source_update_date

    date, status = _detect_source_update_date("The Insolvency and Bankruptcy Code, 2016")
    assert date is None
    assert status == "not_established"
