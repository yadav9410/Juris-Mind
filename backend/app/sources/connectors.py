"""Allow-listed public legal source fetcher; no access-control bypasses."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

ALLOWED_HOSTS = {
    "indiacode.gov.in", "indiacode.nic.in", "egazette.gov.in", "egazette.up.gov.in",
    "sci.gov.in", "scr.sci.gov.in", "allahabadhighcourt.in", "www.allahabadhighcourt.in",
    "elegalix.allahabadhighcourt.in", "judgments.ecourts.gov.in",
    "ecourts.gov.in", "www.ecourts.gov.in",
}

@dataclass
class SourceDocument:
    url: str
    host: str
    title: str | None
    text: str
    retrieved_at: str
    access_method: str = "permitted_public_html"

class PublicLegalSourceConnector:
    """Fetch one public HTML page from an allow-listed official host."""
    def __init__(self, timeout_seconds: float = 20.0):
        self.timeout_seconds = timeout_seconds

    def fetch(self, url: str) -> SourceDocument:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if (parsed.scheme != "https" or host not in ALLOWED_HOSTS
                or parsed.username or parsed.password or parsed.port not in (None, 443)):

            raise ValueError("Only HTTPS URLs on the configured official-source allowlist are permitted.")
        response = httpx.get(url, timeout=self.timeout_seconds, follow_redirects=False,
                             headers={"User-Agent": "JurisMindResearch/1.0"})
        response.raise_for_status()
        final = urlparse(str(response.url))
        if final.scheme != "https" or (final.hostname or "").lower() not in ALLOWED_HOSTS:
            raise ValueError("Redirected outside the official-source allowlist.")
        if len(response.content) > 10 * 1024 * 1024:
            raise ValueError("Source page exceeds the 10 MiB response limit.")
        if "text/html" not in response.headers.get("content-type", "").lower():
            raise ValueError("HTML only; use a separately approved official API/download adapter for other formats.")
        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup(["script", "style", "noscript"]):
            node.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else None
        return SourceDocument(url, host, title, soup.get_text(" ", strip=True),
                              datetime.now(timezone.utc).isoformat())
