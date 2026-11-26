"""Safe discovery plan for official legal portals.

This first connector release deliberately returns official search entry points,
not fabricated search hits. Portal-specific machine adapters are enabled only
after their public interface, terms and rate limits have been verified.
"""
from __future__ import annotations
import re
from urllib.parse import urlparse
from app.source_registry import SOURCES, SOURCE_BY_ID

CATEGORIES = {"legislation", "gazette", "judgment"}

def _clean_query(query: str) -> str:
    value = re.sub(r"\s+", " ", query or "").strip()
    if not value or len(value) < 3 or len(value) > 500:
        raise ValueError("Search query must contain between 3 and 500 characters.")
    return value

def build_official_discovery_plan(query: str, *, jurisdiction: str | None = None,
                                 court: str | None = None, categories: list[str] | None = None) -> dict:
    query = _clean_query(query)
    requested = set(categories or CATEGORIES)
    if not requested.issubset(CATEGORIES):
        raise ValueError("Unsupported source category.")
    selected = []
    for source in SOURCES:
        if source["category"] not in requested:
            continue
        if jurisdiction and jurisdiction.lower() in {"uttar pradesh", "up", "allahabad"}:
            if "uttar_pradesh" not in source["coverage"] and "allahabad" not in source["coverage"] and "high_courts" not in source["coverage"] and "india" not in source["coverage"]:
                continue
        if court and "allahabad" in court.lower() and source["source_id"] not in {"allahabad_elegalix", "ecourts_judgments"}:
            if source["category"] == "judgment":
                continue
        parsed = urlparse(source["search_url"])
        selected.append({
            "source_id": source["source_id"], "source_name": source["name"],
            "source_tier": source["tier"], "category": source["category"],
            "portal_url": source["url"], "search_url": source["search_url"],
            "host": parsed.hostname, "automation_status": source["automation"],
            "coverage": source["coverage"], "notes": source["notes"],
            "query_to_run": query,
            "result_status": "manual_search_required",
        })
    return {
        "query": query, "jurisdiction": jurisdiction, "court": court,
        "source_priority": "official_government_and_courts_first",
        "discovery_status": "portal_entrypoints_prepared",
        "automated_results_count": 0,
        "results": selected,
        "notice": ("These are official portal search entry points, not retrieved authorities. "
                   "Open the portal and run the query; do not treat this plan or a search snippet as evidence. "
                   "A portal-specific automated adapter will be added only after its public interface and access rules are validated."),
    }

def list_official_sources() -> list[dict]:
    return [{k: v for k, v in item.items() if k != "search_url"} | {"search_url": item["search_url"]}
            for item in SOURCES]
