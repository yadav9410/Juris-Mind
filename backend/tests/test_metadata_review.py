import pytest
from pydantic import ValidationError
from app.api.metadata_review import ReviewDecision


def test_correct_requires_corrected_metadata():
    with pytest.raises(ValidationError):
        ReviewDecision(action="correct")


def test_authority_verification_requires_reference_and_evidence():
    with pytest.raises(ValidationError):
        ReviewDecision(action="approve", authority_verified=True)


def test_rejected_record_cannot_be_authority_verified():
    with pytest.raises(ValidationError):
        ReviewDecision(action="reject", authority_verified=True)


def test_valid_correction_and_verification_payload():
    decision = ReviewDecision(
        action="correct",
        corrected_metadata={"document_type": "judgment", "year_candidate": 2025},
        authority_verified=True,
        authority_reference="Official court portal record",
        authority_evidence="Matched case title and date against official record.",
    )
    assert decision.action == "correct"
    assert decision.authority_verified is True
