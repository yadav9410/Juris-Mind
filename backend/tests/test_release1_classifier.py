from app.ingestion.classifier import classify_legal_text


def test_code_named_document_is_classified_as_act():
    result = classify_legal_text(
        "THE INSOLVENCY AND BANKRUPTCY CODE, 2016\nAn Act to consolidate and amend the laws relating to reorganisation and insolvency.",
        "IBC_2016_Original_Gazette.pdf",
    )
    assert result["document_type"] == "act"
    assert result["requires_human_review"] is True


def test_judgment_is_not_classified_as_legislation():
    result = classify_legal_text(
        "SUPREME COURT OF INDIA\nJUDGMENT\nThe appeal is dismissed.\nJudgment pronounced on 12 March 2020.",
        "civil_appeal_judgment.pdf",
    )
    assert result["document_type"] == "judgment"
    assert result["court_candidate"] == "Supreme Court of India"
