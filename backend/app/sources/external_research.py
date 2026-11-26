"""Official-domain external legal search and document retrieval.

Brave is used for discovery. Original documents are fetched only from explicit
official-host allowlists. Retrieval is rate-limited per host, cached in-process,
and never treated as legal authority verification.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import ssl
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urljoin

import fitz
import httpx
import certifi
from bs4 import BeautifulSoup

OFFICIAL_DOMAINS = {
    "india_code": ["indiacode.gov.in", "www.indiacode.gov.in"],
    "egazette_india": ["egazette.gov.in", "egazette.nic.in"],
    "supreme_court_scr": ["scr.sci.gov.in", "sci.gov.in"],
    "allahabad_elegalix": ["elegalix.allahabadhighcourt.in"],
}
SOURCE_META = {
    "india_code": ("India Code", "legislation"),
    "egazette_india": ("e-Gazette of India", "gazette"),
    "supreme_court_scr": ("Supreme Court Reports", "judgment"),
    "allahabad_elegalix": ("Allahabad High Court eLegalix", "judgment"),
}
MAX_BYTES = 20 * 1024 * 1024
MAX_TEXT = 50000
logger = logging.getLogger(__name__)

# Process-local cache/throttle: safe defaults for a single Render web instance.
# This is deliberately conservative; a shared Redis limiter can replace it later.
_CACHE_TTL_SECONDS = 6 * 60 * 60
_HOST_MIN_INTERVAL_SECONDS = {
    # Government portals are deliberately accessed conservatively.
    "egazette.gov.in": 4.0,
    "egazette.nic.in": 4.0,
    "elegalix.allahabadhighcourt.in": 12.0,
}
_DEFAULT_429_COOLDOWN_SECONDS = {
    "egazette.gov.in": 300.0,
    "egazette.nic.in": 300.0,
    "elegalix.allahabadhighcourt.in": 900.0,
}
_cache_lock = threading.Lock()
_fetch_cache: dict[str, tuple[float, dict]] = {}
_host_lock_guard = threading.Lock()
_host_locks: dict[str, threading.Lock] = {}
_host_last_request: dict[str, float] = {}
_host_cooldown_until: dict[str, float] = {}


class ExternalSearchNotConfigured(RuntimeError):
    pass


class OfficialSourceCooldown(RuntimeError):
    """Raised when a host has asked the client to pause requests."""

    http_status = 429

    def __init__(self, host: str, retry_after_seconds: float):
        self.host = host
        self.retry_after_seconds = max(0.0, retry_after_seconds)
        super().__init__(
            f"Official source {host} is in a rate-limit cooldown; "
            f"retry after approximately {int(self.retry_after_seconds)} seconds."
        )


def _ssl_context() -> ssl.SSLContext:
    """Use an up-to-date Mozilla CA bundle; never disable TLS verification."""
    context = ssl.create_default_context(cafile=certifi.where())
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def _host_allowed(url: str, source_id: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in OFFICIAL_DOMAINS[source_id]
        and not parsed.username
        and not parsed.password
        and parsed.port in (None, 443)
    )


def _extract_pdf(content: bytes) -> tuple[str, list[dict], bool]:
    """Extract native PDF text, using OCR only when the runtime has Tesseract.

    A one-character page number is not considered successful legal-text extraction.
    OCR absence is reported rather than silently accepting an empty/scanned PDF.
    """
    pages, locators = [], []
    ocr_used = False
    tesseract_available = shutil.which("tesseract") is not None
    with fitz.open(stream=content, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if len(text) < 80 and tesseract_available:
                try:
                    text_page = page.get_textpage_ocr(language="eng", dpi=220, full=True)
                    ocr_text = page.get_text("text", textpage=text_page).strip()
                    if len(ocr_text) > len(text):
                        text = ocr_text
                        ocr_used = True
                except Exception as exc:
                    logger.info("PDF OCR unavailable for page=%s: %s", i + 1, type(exc).__name__)
            if text:
                pages.append(text)
                locators.append({"page": i + 1, "text": text[:2500]})
    return "\n\n".join(pages).strip(), locators, ocr_used


def _html_document_candidates(soup: BeautifulSoup, base_url: str, source_id: str) -> list[str]:
    """Find embedded official document links on an India Code landing page."""
    if source_id != "india_code":
        return []
    candidates: list[str] = []
    for node in soup.find_all(["iframe", "embed", "object", "a"]):
        raw = node.get("src") or node.get("data") or node.get("href")
        if not raw:
            continue
        candidate = urljoin(base_url, raw.strip())
        path = urlparse(candidate).path.lower()
        label = " ".join([
            str(node.get("title") or ""), str(node.get("aria-label") or ""),
            node.get_text(" ", strip=True) if getattr(node, "name", None) == "a" else "",
        ]).lower()
        looks_like_document = (
            path.endswith(".pdf") or "bitstream" in path or "download" in path
            or "viewcontent" in path or "pdf" in label or "download" in label
        )
        if looks_like_document and _host_allowed(candidate, source_id) and candidate not in candidates:
            candidates.append(candidate)
    return candidates[:3]


def _meaningful_legal_text(text: str, content_kind: str) -> bool:
    """Reject tiny PDF text layers and generic pages masquerading as documents."""
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if len(normalized) < 80:
        return False
    if content_kind == "pdf":
        # PDFs should contain a substantive text layer, not just a page number/header.
        return len(normalized.split()) >= 12
    return len(normalized.split()) >= 12


def _extract_targeted_statutory_provisions(text: str, query: str) -> dict[str, str]:
    """Extract explicitly requested numbered Act sections without rewriting them."""
    requested = re.findall(r"\bsection\s+(\d+[A-Za-z]?)\b", query or "", flags=re.I)
    output: dict[str, str] = {}
    if not requested or not text:
        return output
    for number in dict.fromkeys(requested):
        heading = re.compile(
            rf"(?im)^\s*{re.escape(number)}\.\s+[^\n]{{5,240}}"
        )
        match = heading.search(text)
        if not match:
            continue
        next_heading = re.compile(r"(?m)^\s*\d+[A-Za-z]?\.\s+[A-Z][^\n]{5,240}")
        end_match = next_heading.search(text, match.end())
        end = end_match.start() if end_match else len(text)
        provision = text[match.start():end].strip()
        if len(provision) >= 80:
            output[number] = provision
    return output


def _host_pacing(host: str) -> None:
    """Serialize requests per host and enforce both pacing and 429 cooldown."""
    with _host_lock_guard:
        lock = _host_locks.setdefault(host, threading.Lock())
    with lock:
        now = time.monotonic()
        cooldown_until = _host_cooldown_until.get(host, 0.0)
        if cooldown_until > now:
            raise OfficialSourceCooldown(host, cooldown_until - now)
        interval = _HOST_MIN_INTERVAL_SECONDS.get(host, 1.0)
        wait_for = interval - (now - _host_last_request.get(host, 0.0))
        if wait_for > 0:
            time.sleep(wait_for)
        _host_last_request[host] = time.monotonic()


def _set_host_cooldown(host: str, response: httpx.Response) -> float:
    retry_after = _retry_after_seconds(response)
    if retry_after is None:
        retry_after = _DEFAULT_429_COOLDOWN_SECONDS.get(host, 300.0)
    with _host_lock_guard:
        _host_cooldown_until[host] = time.monotonic() + retry_after
    return retry_after


def _retry_after_seconds(response: httpx.Response | None) -> float | None:
    if response is None:
        return None
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
            return max(0.0, (dt - datetime.now(timezone.utc)).total_seconds())
        except Exception:
            return None


def _fetch_official_document(url: str, source_id: str, timeout: float = 18.0, *, _allow_embedded: bool = True) -> dict:
    if not _host_allowed(url, source_id):
        raise ValueError("Search result URL is outside the selected official source host allowlist.")

    cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    now = time.time()
    with _cache_lock:
        cached = _fetch_cache.get(cache_key)
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            value = dict(cached[1])
            value["cache_status"] = "hit"
            return value

    parsed = urlparse(url)
    host = parsed.hostname or ""
    current_url = url
    response = None
    # At most two connection attempts. HTTP 429 is not blindly retried.
    for attempt in range(2):
        _host_pacing(host)
        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=False,
                verify=_ssl_context(),
                headers={"User-Agent": "JurisMindLegalResearch/1.0"},
            ) as client:
                response = client.get(current_url)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            logger.warning(
                "Official source connection failure: source_id=%s host=%s error_type=%s detail=%s attempt=%s",
                source_id, host, type(exc).__name__, str(exc)[:240], attempt + 1,
            )
            if attempt == 0:
                time.sleep(0.8)
                continue
            raise
        logger.info(
            "Official document HTTP response: source_id=%s host=%s status=%s content_type=%s bytes=%s",
            source_id, host, response.status_code,
            response.headers.get("content-type", "unknown"), len(response.content),
        )
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location:
                response.raise_for_status()
            redirected = urljoin(current_url, location)
            if not _host_allowed(redirected, source_id):
                raise ValueError("Official source redirect points outside its allowlisted host.")
            current_url = redirected
            continue
        if response.status_code == 429:
            delay = _set_host_cooldown(host, response)
            logger.warning(
                "Official source rate limited: source_id=%s host=%s retry_after_seconds=%s; host cooldown activated",
                source_id, host, int(delay),
            )
            # Do not retry automatically. Subsequent requests are suppressed during cooldown.
            response.raise_for_status()
        if response.status_code in {500, 502, 503, 504} and attempt == 0:
            time.sleep(1.0)
            continue
        response.raise_for_status()
        break
    if response is None:
        raise RuntimeError("Official source request did not produce an HTTP response.")

    final_url = str(response.url)
    if not _host_allowed(final_url, source_id):
        raise ValueError("Official source resolved outside its allowlisted host.")
    if len(response.content) > MAX_BYTES:
        raise ValueError("Official document exceeds the retrieval size limit.")

    content_type = response.headers.get("content-type", "").lower()
    downloaded = True
    extraction_error = None
    ocr_used = False
    embedded_document_url = None
    try:
        if "application/pdf" in content_type or response.content[:5] == b"%PDF-":
            text, pages, ocr_used = _extract_pdf(response.content)
            kind = "pdf"
            if not _meaningful_legal_text(text, kind):
                extraction_error = (
                    "PDF contains no substantial selectable text; OCR is unavailable or did not recover text."
                    if not ocr_used else "OCR did not recover substantial legal text."
                )
        elif "text/html" in content_type or "application/xhtml+xml" in content_type:
            soup = BeautifulSoup(response.text, "html.parser")
            candidates = _html_document_candidates(soup, final_url, source_id) if _allow_embedded else []
            for node in soup(["script", "style", "noscript", "nav", "footer", "header"]):
                node.decompose()
            # Prefer the page's substantive text; if it is only a viewer shell, fetch
            # one same-host embedded PDF/bitstream as the actual statutory document.
            text = soup.get_text(" ", strip=True)
            pages = []
            kind = "html"
            if not _meaningful_legal_text(text, kind) and candidates:
                embedded_document_url = candidates[0]
                embedded = _fetch_official_document(
                    embedded_document_url, source_id, timeout=timeout, _allow_embedded=False
                )
                if embedded.get("extracted"):
                    result = dict(embedded)
                    result["landing_page_url"] = final_url
                    result["source_url"] = embedded.get("source_url", embedded_document_url)
                    result["access_method"] = "official_landing_page_embedded_document"
                    result["cache_status"] = "miss"
                    with _cache_lock:
                        _fetch_cache[cache_key] = (time.time(), dict(result))
                    return result
                extraction_error = embedded.get("extraction_error") or "Embedded official document could not be extracted."
        else:
            raise ValueError(f"Unsupported official document content type: {content_type or 'unknown'}")
    except Exception as exc:
        text, pages, kind = "", [], "unknown"
        extraction_error = f"{type(exc).__name__}: {str(exc)[:250]}"

    meaningful = _meaningful_legal_text(text, kind)
    if text.strip() and not meaningful and not extraction_error:
        extraction_error = "Downloaded page contained too little substantive text to count as document extraction."

    result = {
        "source_url": final_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "content_type": kind,
        "content_sha256": hashlib.sha256(response.content).hexdigest(),
        "downloaded": downloaded,
        "extracted": meaningful,
        "extracted_text": text[:MAX_TEXT] if meaningful else "",
        "extraction_quality": "substantive_text" if meaningful else "insufficient_text",
        "ocr_used": ocr_used,
        "embedded_document_url": embedded_document_url,
        "page_evidence": pages[:8],
        "document_retrieved": meaningful,  # backwards-compatible legacy field
        "extraction_error": extraction_error,
        "verification_status": "not_verified",
        "access_method": "brave_index_then_direct_official_fetch",
        "cache_status": "miss",
        "http_status": response.status_code,
    }
    with _cache_lock:
        _fetch_cache[cache_key] = (time.time(), dict(result))
    return result


_QUERY_STOPWORDS = {
    "research", "identify", "provide", "include", "including", "relevant",
    "under", "indian", "central", "law", "use", "primary", "source",
    "supplementary", "prefer", "official", "court", "documents", "document",
    "provide", "concise", "memo", "case", "citations", "dates", "paragraphs",
    "source", "links", "verification", "status", "highlight", "missing",
    "evidence", "unavailable", "sources", "limitations", "mark", "unverified",
    "results", "verified", "authorities", "and", "the", "a", "an", "of", "for",
    "to", "with", "as", "is", "are", "by", "on", "from", "all", "where",
}


def _issue_terms(query: str, limit: int = 9) -> str:
    """Reduce a memo-style instruction to its legal issue, not its output instructions."""
    text = re.sub(r"https?://\S+", " ", query, flags=re.I)
    # Keep the first request sentence/phrase; later sentences are usually output rules.
    text = re.split(r"[.!?;]\s+", text, maxsplit=1)[0]
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9&'/-]*", text)
    kept = []
    for token in tokens:
        normalized = token.lower()
        if normalized in _QUERY_STOPWORDS or len(normalized) < 2:
            continue
        if normalized not in {item.lower() for item in kept}:
            kept.append(token)
        if len(kept) >= limit:
            break
    section_match = re.search(r"\bsection\s+([0-9A-Za-z()/-]+)", text, flags=re.I)
    if section_match:
        section_phrase = f"Section {section_match.group(1)}"
        kept = [item for item in kept if item.lower() != "section"]
        kept.append(section_phrase)
    return " ".join(kept) or "Indian law"


def _build_source_query(query: str, source_id: str, jurisdiction: str | None,
                        court: str | None) -> str:
    """Build a short source-specific query suitable for the Brave API."""
    issue = _issue_terms(query)
    if source_id == "india_code":
        terms = "Act section official statutory text amendment"
    elif source_id == "egazette_india":
        terms = "Gazette notification amendment commencement"
    elif source_id == "supreme_court_scr":
        terms = "Supreme Court judgment case citation"
    else:
        terms = "Allahabad High Court judgment case citation"
    jurisdiction_context = ""
    if jurisdiction and jurisdiction.lower() not in {"india", "other / not specified"}:
        jurisdiction_context = " " + jurisdiction[:40]
    court_context = ""
    if court and source_id in {"supreme_court_scr", "allahabad_elegalix"}:
        court_context = " " + court[:45]
    # Keep q comfortably below provider query-length limits even for long UI prompts.
    return re.sub(r"\s+", " ", f"{issue} {terms}{jurisdiction_context}{court_context}").strip()[:220]


def search_official_sources(query: str, *, jurisdiction: str | None = None,
                            court: str | None = None, categories: list[str] | None = None,
                            max_results_per_source: int = 5, timeout: float = 20.0) -> dict:
    """Search official domains and retrieve matching original HTML/PDF documents."""
    query = re.sub(r"\s+", " ", (query or "")).strip()
    if len(query) < 3 or len(query) > 500:
        raise ValueError("External research query must contain 3 to 500 characters.")
    token = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not token:
        raise ExternalSearchNotConfigured("BRAVE_SEARCH_API_KEY is not configured.")

    requested = set(categories or ["legislation", "gazette", "judgment"])
    invalid = requested - {"legislation", "gazette", "judgment"}
    if invalid:
        raise ValueError("Unsupported external research category.")
    source_ids = [
        sid for sid, (_name, category) in SOURCE_META.items()
        if category in requested
        and not (court and "allahabad" in court.lower() and sid == "supreme_court_scr")
        and not (court and "supreme" in court.lower() and sid == "allahabad_elegalix")
    ]

    def search_one(sid: str) -> tuple[list[dict], list[dict]]:
        source_name, category = SOURCE_META[sid]
        domain_query = " OR ".join(f"site:{d}" for d in OFFICIAL_DOMAINS[sid])
        tailored_query = _build_source_query(query, sid, jurisdiction, court)
        brave_query = f"{domain_query} {tailored_query}"
        params = {
            "q": brave_query[:300],
            "count": max(1, min(max_results_per_source, 10)),
            "country": "IN",
            "search_lang": "en",
        }
        local_results, local_errors = [], []
        logger.info(
            "Brave official-source search started: source_id=%s category=%s tailored_query_length=%s",
            sid, category, len(tailored_query),
        )
        try:
            response = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                params=params,
                headers={"Accept": "application/json", "X-Subscription-Token": token},
                timeout=timeout,
            )
            logger.info("Brave API response: source_id=%s status=%s", sid, getattr(response, "status_code", "unknown"))
            response.raise_for_status()
            hits = (response.json().get("web") or {}).get("results") or []
            logger.info("Brave API results: source_id=%s hit_count=%s", sid, len(hits))
        except Exception as exc:
            response_obj = getattr(exc, "response", None)
            status_code = getattr(response_obj, "status_code", None)
            response_detail = ""
            if response_obj is not None:
                try:
                    response_detail = response_obj.text[:500]
                except Exception:
                    response_detail = ""
            failure_category = (
                "provider_bad_request" if status_code == 422 else
                "provider_rate_limited" if status_code == 429 else
                "provider_http_error" if status_code else "provider_connection_error"
            )
            logger.warning(
                "Brave official-source search failed: source_id=%s status=%s category=%s detail=%s",
                sid, status_code, failure_category, response_detail[:240],
            )
            return [], [{
                "source_id": sid, "source_name": source_name, "stage": "search",
                "failure_category": failure_category, "http_status": status_code,
                "error_type": type(exc).__name__,
                "error": (response_detail or str(exc))[:500],
                "query_sent": params["q"],
            }]

        for hit in hits[:max_results_per_source]:
            url = hit.get("url") or ""
            if not _host_allowed(url, sid):
                continue
            item = {
                "source_id": sid, "source_name": source_name, "source_tier": "primary",
                "category": category, "title": hit.get("title"),
                "search_snippet": hit.get("description"), "source_url": url,
                "retrieval_status": "search_result_only",
                "verification_status": "not_verified", "downloaded": False,
                "extracted": False,
            }
            try:
                fetched = _fetch_official_document(url, sid, timeout=min(timeout, 20.0))
                item.update(fetched)
                if sid == "india_code" and fetched.get("extracted"):
                    provision_extracts = _extract_targeted_statutory_provisions(
                        fetched.get("extracted_text", ""), query
                    )
                    requested_sections = re.findall(r"\bsection\s+(\d+[A-Za-z]?)\b", query, flags=re.I)
                    item["targeted_provisions"] = provision_extracts
                    item["targeted_provision_status"] = (
                        "extracted" if provision_extracts else
                        "not_found_in_extracted_text" if requested_sections else "not_requested"
                    )
                # Normalize older fetcher payloads without overriding explicit new booleans.
                if "downloaded" not in fetched:
                    item["downloaded"] = bool(fetched.get("document_retrieved") or fetched.get("content_sha256"))
                if "extracted" not in fetched:
                    item["extracted"] = bool(fetched.get("extracted_text") or fetched.get("document_retrieved"))
                if item.get("downloaded") and item.get("extracted"):
                    item["retrieval_status"] = "downloaded_and_extracted"
                elif item.get("downloaded"):
                    item["retrieval_status"] = "downloaded_extraction_failed"
                else:
                    item["retrieval_status"] = "download_failed"
            except Exception as exc:
                item["retrieval_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                item["retrieval_error_type"] = type(exc).__name__
                if isinstance(exc, httpx.ConnectError) and "CERTIFICATE_VERIFY_FAILED" in str(exc):
                    item["retrieval_failure_category"] = "tls_certificate_verification"
                elif isinstance(exc, OfficialSourceCooldown):
                    item["retrieval_failure_category"] = "host_rate_limit_cooldown"
                elif getattr(getattr(exc, "response", None), "status_code", None) == 429:
                    item["retrieval_failure_category"] = "http_rate_limited"
                elif getattr(getattr(exc, "response", None), "status_code", None) == 403:
                    item["retrieval_failure_category"] = "access_denied"
                item["http_status"] = (
                    getattr(getattr(exc, "response", None), "status_code", None)
                    or getattr(exc, "http_status", None)
                )
                if isinstance(exc, OfficialSourceCooldown):
                    item["retry_after_seconds"] = int(exc.retry_after_seconds)
                item["downloaded"] = False
                item["extracted"] = False
                item["retrieval_status"] = "download_failed"
                logger.warning(
                    "Official document retrieval failed: source_id=%s host=%s error_type=%s http_status=%s",
                    sid, urlparse(url).hostname, type(exc).__name__, item["http_status"],
                )
            local_results.append(item)
        return local_results, local_errors

    results, errors = [], []
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(source_ids)))) as pool:
        futures = [pool.submit(search_one, sid) for sid in source_ids]
        for future in as_completed(futures):
            source_results, source_errors = future.result()
            results.extend(source_results)
            errors.extend(source_errors)

    search_count = len(results)
    downloaded_count = sum(bool(r.get("downloaded")) for r in results)
    extracted_count = sum(bool(r.get("extracted")) for r in results)
    failed_count = sum(r.get("retrieval_status") == "download_failed" for r in results) + len(errors)
    source_summaries = {}
    for sid, (source_name, _category) in SOURCE_META.items():
        source_rows = [r for r in results if r.get("source_id") == sid]
        source_error_rows = [e for e in errors if e.get("source_id") == sid]
        source_summaries[sid] = {
            "source_name": source_name,
            "search_status": "failed" if source_error_rows else ("completed" if source_rows else "no_results"),
            "search_errors": source_error_rows,
            "search_results_count": len(source_rows),
            "downloaded_documents_count": sum(bool(r.get("downloaded")) for r in source_rows),
            "extracted_documents_count": sum(bool(r.get("extracted")) for r in source_rows),
            "failed_retrievals_count": sum(r.get("retrieval_status") == "download_failed" for r in source_rows),
        }
    logger.info(
        "External official-source search finished: sources=%s search_results=%s downloaded=%s extracted=%s failed=%s verified=0",
        len(source_ids), search_count, downloaded_count, extracted_count, failed_count,
    )
    return {
        "query": query, "jurisdiction": jurisdiction, "court": court,
        "source_priority": "official_government_and_courts_first",
        "provider": "brave_search_api",
        "external_search_status": (
            "provider_error" if errors and not results else
            "partial" if errors and results else
            "completed" if results else "no_results"
        ),
        "source_count": len(source_ids),
        "result_count": search_count,
        "search_results_count": search_count,
        "downloaded_documents_count": downloaded_count,
        "extracted_documents_count": extracted_count,
        "verified_authorities_count": 0,
        "failed_retrievals_count": failed_count,
        "document_count": downloaded_count,  # backwards-compatible alias
        "results": results,
        "source_summaries": source_summaries,
        "source_errors": errors,
        "verification_status": "not_verified",
        "notice": "Search results are research leads. Downloaded documents and extracted text are not authority-verified or proposition-verified. Provider status is reported separately for each source.",
    }
