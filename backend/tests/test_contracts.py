from datetime import date
import pytest
from pydantic import ValidationError
from app.contracts.models import LegalResearchRequest, Jurisdiction, SourceReference
from app.contracts.enums import LegalDomain, SourceTier, SourceType


def test_default_jurisdiction_is_india_up():
    request = LegalResearchRequest(query="Explain legal requirements for a contract dispute.")
    assert request.jurisdiction.country_code == "IN"
    assert request.jurisdiction.state_code == "UP"
    assert request.output_formats == ["pdf", "docx"]


def test_accepts_multiple_domains():
    request = LegalResearchRequest(
        query="Research a dispute involving an employment contract and personal data.",
        requested_domains=[LegalDomain.CONTRACT, LegalDomain.EMPLOYMENT_LABOUR],
        jurisdiction=Jurisdiction(state_code="UP", state_name="Uttar Pradesh"),
        as_of_date=date(2026, 1, 1),
    )
    assert len(request.requested_domains) == 2


def test_rejects_too_short_query():
    with pytest.raises(ValidationError):
        LegalResearchRequest(query="help")


def test_source_reference_requires_valid_url_when_provided():
    source = SourceReference(
        source_id="test",
        title="Example Act",
        source_type=SourceType.LEGISLATION,
        source_tier=SourceTier.PRIMARY,
        url="https://www.indiacode.nic.in/",
    )
    assert str(source.url).startswith("https://")
