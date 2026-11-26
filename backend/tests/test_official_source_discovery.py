from app.source_registry import SOURCES
from app.sources.discovery import build_official_discovery_plan
from app.sources.connectors import ALLOWED_HOSTS

def test_official_registry_prioritizes_primary_sources_and_updated_hosts():
    assert SOURCES
    assert all(s["tier"] == "primary" for s in SOURCES)
    ids = {s["source_id"] for s in SOURCES}
    assert {"india_code", "egazette_india", "supreme_court_scr", "allahabad_elegalix"} <= ids
    assert "indiacode.gov.in" in ALLOWED_HOSTS
    assert "elegalix.allahabadhighcourt.in" in ALLOWED_HOSTS

def test_discovery_plan_is_explicitly_not_search_results():
    result = build_official_discovery_plan("IBC Section 7", jurisdiction="India")
    assert result["automated_results_count"] == 0
    assert result["discovery_status"] == "portal_entrypoints_prepared"
    assert all(row["result_status"] == "manual_search_required" for row in result["results"])
    assert {row["source_id"] for row in result["results"]} >= {"india_code", "egazette_india", "supreme_court_scr"}

def test_uttar_pradesh_allahabad_scope_includes_elegalix():
    result = build_official_discovery_plan("Article 226 writ maintainability",
                                          jurisdiction="Uttar Pradesh", court="Allahabad High Court")
    ids = {row["source_id"] for row in result["results"]}
    assert "allahabad_elegalix" in ids

def test_invalid_query_rejected():
    import pytest
    with pytest.raises(ValueError):
        build_official_discovery_plan("  ")
