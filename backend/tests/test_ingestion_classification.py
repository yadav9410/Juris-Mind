import json
import fitz
from app.ingestion.classifier import classify_legal_text
from app.ingestion.extractors import extract_document


def test_classifies_act_and_keeps_review_flag():
    text = """THE INFORMATION TECHNOLOGY ACT, 2000
    An Act to provide legal recognition for transactions carried out by means of electronic data interchange.
    Be it enacted by Parliament."""
    result = classify_legal_text(text, "it_act.pdf")
    assert result["document_type"] == "act"
    assert result["year_candidate"] == 2000
    assert result["requires_human_review"] is True


def test_extracts_supreme_court_neutral_citation():
    result = classify_legal_text(
        "SUPREME COURT OF INDIA\nA v B\n2024 INSC 123\nJudgment"
    )
    assert result["court_candidate"] == "Supreme Court of India"
    assert result["neutral_citation_candidate"] == "2024 INSC 123"


def test_native_pdf_extraction_does_not_need_ocr(tmp_path):
    path = tmp_path / "native.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "THE INDIAN CONTRACT ACT 1872 " * 8)
    doc.save(path)
    doc.close()
    result = extract_document(path, "application/pdf", ocr_enabled=True)
    assert result.page_count == 1
    assert result.needs_ocr is False
    assert result.ocr_used is False


def test_extracts_candidate_jurisdiction_and_keeps_it_unverified():
    result = classify_legal_text(
        "ALLAHABAD HIGH COURT\nJudgment\nPronounced: 12 February 2025\n"
        "The High Court of Judicature at Allahabad considers this matter."
    )
    assert result["jurisdiction_candidate"] == "Uttar Pradesh, India"
    assert result["decision_date_candidate"] == "2025-02-12"
    assert result["requires_human_review"] is True
