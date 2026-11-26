import fitz
from app.ingestion.extractors import extract_pdf
from app.ingestion.structuring import structure_legal_text, LegalChunk


def test_pdf_extraction_retains_one_based_page_texts(tmp_path):
    path = tmp_path / "two_pages.pdf"
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "Section 1. Short title\nThis Act may be called the Example Act.")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "Section 2. Definitions\nIn this Act, unless the context otherwise requires.")
    doc.save(path)
    doc.close()

    result = extract_pdf(path, ocr_enabled=False)
    assert result.page_count == 2
    assert [number for number, _ in result.page_texts] == [1, 2]
    assert "Section 1" in result.page_texts[0][1]
    assert "Section 2" in result.page_texts[1][1]


def test_page_chunks_keep_source_page_pinpoints():
    text = "Section 1. Short title\nThis Act may be called the Example Act."
    chunks = structure_legal_text(text, "act")
    assert chunks
    page_chunk = LegalChunk(
        ordinal=1, chunk_type=chunks[0].chunk_type, locator=chunks[0].locator,
        heading=chunks[0].heading, text=chunks[0].text, page_start=4, page_end=4,
    )
    assert page_chunk.page_start == 4
    assert page_chunk.page_end == 4
