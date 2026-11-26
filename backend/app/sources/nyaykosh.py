"""Read-only Nyaykosh (NeGD Law as Code) REST API connector.

Only endpoint shapes publicly demonstrated by Nyaykosh are implemented:
  GET /v1/laws/{law_id}
  GET /v1/laws/{law_id}/penalties

A successful API response is provider data, not independent legal-authority
verification. Always retain the official Gazette/PDF/XML cross-check separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urljoin

import httpx

DEFAULT_BASE_URL = "https://lawascode.negd.in/"
NYAYKOSH_SOURCE = {
    "source_id": "nyaykosh_negd",
    "name": "Nyaykosh (NeGD Law as Code)",
    "url": DEFAULT_BASE_URL,
    "coverage_note": "Limited published legislation coverage; confirm the requested Act exists before relying on this source.",
    "source_classification": "government_structured_data",
    "verification_status": "not_independently_verified",
}
_LAW_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")


class NyaykoshError(RuntimeError):
    """Base exception for Nyaykosh connector failures."""


class NyaykoshNotFound(NyaykoshError):
    """The requested law is not present at the documented API endpoint."""


class NyaykoshResponseError(NyaykoshError):
    """The provider returned an unexpected or invalid response."""


@dataclass(frozen=True)
class NyaykoshResponse:
    endpoint: str
    retrieved_at: str
    http_status: int
    data: dict[str, Any] | list[Any]
    provider: str = "Nyaykosh (NeGD Law as Code)"
    verification_status: str = "not_independently_verified"


class NyaykoshClient:
    """Small, bounded, read-only client for Nyaykosh's public REST API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        normalized = base_url.rstrip("/") + "/"
        if not normalized.startswith("https://"):
            raise ValueError("Nyaykosh base URL must use HTTPS.")
        self.base_url = normalized
        self.timeout_seconds = timeout_seconds
        self._client = client

    @staticmethod
    def _validate_law_id(law_id: str) -> str:
        value = (law_id or "").strip().lower()
        if not _LAW_ID_RE.fullmatch(value):
            raise ValueError("law_id must be a lowercase alphanumeric slug with optional hyphens.")
        return value

    def _get(self, path: str) -> NyaykoshResponse:
        endpoint = urljoin(self.base_url, path.lstrip("/"))
        if not endpoint.startswith(self.base_url):
            raise ValueError("Invalid Nyaykosh endpoint.")
        own_client = self._client is None
        client = self._client or httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=False,
            headers={"Accept": "application/json", "User-Agent": "JurisMind/1.0 (+read-only legal data integration)"},
        )
        try:
            response = client.get(endpoint)
            if response.status_code == 404:
                raise NyaykoshNotFound(f"Nyaykosh does not expose this resource: {path}")
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "json" not in content_type:
                raise NyaykoshResponseError(
                    f"Expected JSON from Nyaykosh; received {content_type or 'unknown content type'}."
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise NyaykoshResponseError("Nyaykosh returned invalid JSON.") from exc
            if not isinstance(payload, (dict, list)):
                raise NyaykoshResponseError("Nyaykosh JSON response must be an object or array.")
            return NyaykoshResponse(
                endpoint=str(response.url),
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                http_status=response.status_code,
                data=payload,
            )
        except httpx.HTTPStatusError as exc:
            raise NyaykoshError(
                f"Nyaykosh HTTP error {exc.response.status_code} for {path}."
            ) from exc
        except httpx.HTTPError as exc:
            raise NyaykoshError(f"Nyaykosh request failed: {type(exc).__name__}.") from exc
        finally:
            if own_client:
                client.close()

    def get_law(self, law_id: str) -> NyaykoshResponse:
        """Fetch structured Act/rule JSON using the documented law endpoint."""
        slug = self._validate_law_id(law_id)
        return self._get(f"v1/laws/{slug}")

    def get_penalties(self, law_id: str) -> NyaykoshResponse:
        """Fetch the documented penalty schedule for an Act/rule."""
        slug = self._validate_law_id(law_id)
        return self._get(f"v1/laws/{slug}/penalties")

    def get_law_with_penalties(self, law_id: str) -> dict[str, Any]:
        """Fetch both documented resources without conflating their provenance."""
        law = self.get_law(law_id)
        try:
            penalties = self.get_penalties(law_id)
            penalty_status = "retrieved"
            penalty_data: Any = penalties.data
            penalty_endpoint = penalties.endpoint
        except NyaykoshNotFound:
            penalty_status = "not_available"
            penalty_data = None
            penalty_endpoint = None
        return {
            "source_id": "nyaykosh_negd",
            "law": {
                "endpoint": law.endpoint,
                "retrieved_at": law.retrieved_at,
                "http_status": law.http_status,
                "data": law.data,
            },
            "penalties": {
                "status": penalty_status,
                "endpoint": penalty_endpoint,
                "data": penalty_data,
            },
            "verification_status": "not_independently_verified",
            "verification_note": "Cross-check the official Gazette/PDF and applicable commencement/amendment records before legal reliance.",
        }
