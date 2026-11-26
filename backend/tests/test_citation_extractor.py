from app.citations.extractor import extract_citations, normalize_citation

def test_extracts_indian_neutral_and_reported_citations():
    text = "The Supreme Court considered the issue in 2024 INSC 123 and (1979) 2 SCC 409."
    items = extract_citations(text)
    assert [x.citation_type for x in items] == ["neutral", "scc"]
    assert items[0].normalized["canonical"] == "2024 INSC 123"
    assert items[1].normalized["reporter"] == "SCC"

def test_extracts_statutory_provision_and_preserves_offsets():
    text = "See Section 3(2) of the Act and Article 14."
    items = extract_citations(text)
    assert len(items) == 2
    assert items[0].citation_type == "statutory"
    assert items[0].citation_text == "Section 3(2)"
    assert text[items[0].start_offset:items[0].end_offset] == items[0].citation_text
    assert items[1].normalized["provision_ref"] == "Article 14"

def test_empty_text_returns_no_candidates():
    assert extract_citations("") == []

def test_normalization_does_not_invent_missing_fields():
    result = normalize_citation("AIR 1973 SC 1461", "air")
    assert result["year"] == 1973
    assert result["reporter"] == "AIR"
