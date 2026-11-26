from app.ingestion.structuring import structure_legal_text


def test_act_sections_are_separate_chunks():
    text = """PREAMBLE OF THE ACT

Section 1. Short title and commencement
This Act may be called the Example Act.

Section 2. Definitions
In this Act, unless the context otherwise requires, terms have meanings."""
    chunks = structure_legal_text(text, "act")
    assert [c.locator for c in chunks if c.chunk_type == "provision"] == [
        "Section 1", "Section 2"
    ]
    assert any(c.chunk_type == "preamble" for c in chunks)


def test_judgment_numbered_paragraphs_are_separate():
    text = """JUDGMENT

1. The appeal concerns interpretation of the statute.

2. We have heard learned counsel and examined the record."""
    chunks = structure_legal_text(text, "judgment")
    paragraphs = [c for c in chunks if c.chunk_type == "judgment_paragraph"]
    assert [c.locator for c in paragraphs] == ["1", "2"]


def test_long_text_is_bounded():
    text = "Paragraph one. " + ("important legal words " * 300)
    chunks = structure_legal_text(text, "unknown", max_chars=700, overlap=80)
    assert len(chunks) > 1
    assert all(len(c.text) <= 700 for c in chunks)


def test_invalid_chunk_settings_rejected():
    try:
        structure_legal_text("text", "act", max_chars=100, overlap=10)
        assert False, "Expected ValueError"
    except ValueError:
        pass
