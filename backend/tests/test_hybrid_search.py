from datetime import datetime, timezone
import pytest
from app.search.hybrid import search_legal_chunks_hybrid, HYBRID_SEARCH_SQL

class FakeRow:
    def __init__(self, data):
        self._mapping = data

class FakeResult:
    def __init__(self, rows):
        self.rows = rows
    def __iter__(self):
        return iter(self.rows)

class FakeSession:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.statement = None
        self.params = None
    def execute(self, statement, params):
        self.statement = statement
        self.params = params
        return FakeResult(self.rows)

def test_hybrid_search_passes_filters_and_returns_mappings():
    db = FakeSession([FakeRow({"chunk_id": "c1", "hybrid_score": 0.8})])
    rows = search_legal_chunks_hybrid(
        db, "section 420", document_type="act", chunk_type="provision",
        locator="Section 420", limit=7,
    )
    assert rows == [{"chunk_id": "c1", "hybrid_score": 0.8}]
    assert db.params["document_type"] == "act"
    assert db.params["chunk_type"] == "provision"
    assert db.params["locator"] == "Section 420"
    assert db.params["limit"] == 7
    assert "ts_rank_cd" in str(db.statement)
    assert "ts_headline" in str(db.statement)

def test_empty_query_is_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        search_legal_chunks_hybrid(FakeSession(), "   ")

def test_limit_is_bounded():
    with pytest.raises(ValueError, match="between 1 and 100"):
        search_legal_chunks_hybrid(FakeSession(), "contract", limit=101)

def test_invalid_date_window_is_rejected():
    start = datetime(2025, 1, 2, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="earlier"):
        search_legal_chunks_hybrid(FakeSession(), "contract", created_after=start, created_before=end)

def test_sql_uses_parameterized_filters_and_discovery_statuses():
    sql = str(HYBRID_SEARCH_SQL)
    assert "j.status IN ('extracted', 'needs_ocr')" in sql
    assert ":document_type" in sql and ":chunk_type" in sql
    assert "OR exact_phrase" in sql
    assert "OR locator_match" in sql


def test_hybrid_search_passes_authority_metadata_filters():
    db = FakeSession([])
    search_legal_chunks_hybrid(
        db, "natural justice", jurisdiction="Uttar Pradesh, India",
        court="Allahabad High Court", decision_year=2025,
    )
    assert db.params["jurisdiction"] == "Uttar Pradesh, India"
    assert db.params["court"] == "Allahabad High Court"
    assert db.params["decision_year"] == 2025
    sql = str(db.statement)
    assert "jurisdiction_candidate" in sql
    assert "court_candidate" in sql
    assert "year_candidate" in sql


def test_hybrid_search_builds_bounded_or_fallback_query():
    db = FakeSession([])
    search_legal_chunks_hybrid(
        db,
        "What is the statutory test for bail under Section 438 and CrPC?",
    )
    assert db.params["fallback_query"] == "statutory | test | bail | section | 438 | crpc"
    sql = str(db.statement)
    assert "to_tsquery('simple', :fallback_query)" in sql
    assert "search_vector @@ fallback_query" in sql
    assert "LIKE '%, india'" in sql
    assert "numnode(fallback_query) >= 1" in sql
    assert "ts_headline" in sql
