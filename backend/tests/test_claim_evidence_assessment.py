from app.claims.assessor import assess_claim

def test_candidate_support_requires_high_overlap_and_multiple_terms():
    result = assess_claim(
        "The resolution applicant cannot withdraw the approved resolution plan",
        [{"evidence_id":"p1","text":"The resolution applicant cannot withdraw or modify the approved resolution plan after approval."}],
    )
    assert result["assessment_status"] == "candidate_support"
    assert result["evidence_assessments"][0]["status"] == "candidate_support"
    assert any("not a legal entailment" in item for item in result["limitations"])

def test_weak_overlap_is_not_reported_as_verified_support():
    result = assess_claim(
        "A resolution applicant may withdraw a plan after approval",
        [{"text":"The applicant filed an appeal against the order."}],
    )
    assert result["assessment_status"] in {"weak_overlap", "no_support_found"}
    assert result["assessment_status"] != "verified"

def test_no_overlap_does_not_claim_falsity():
    result = assess_claim(
        "Whether a statutory resolution plan can be modified after approval",
        [{"text":"The court considered limitation and territorial jurisdiction."}],
    )
    assert result["assessment_status"] == "no_support_found"
    assert any("does not prove the claim is false" in item for item in result["limitations"])

def test_empty_evidence_terms_are_safe():
    result = assess_claim("This is a sufficiently long legal claim", [{"text":"---"}])
    assert result["assessment_status"] == "no_support_found"
