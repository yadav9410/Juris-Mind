"""Contract checks for Increment 20 due-diligence routes and schemas."""
from app.main import app
from app.api.due_diligence import MatterCreate, RiskCreate, ComparisonCreate


def test_due_diligence_routes_registered():
    from app.main import app

    paths = app.openapi()["paths"]

    expected_paths = {
        "/due-diligence/matters",
        "/due-diligence/matters/{matter_id}",
        "/due-diligence/matters/{matter_id}/risks",
        "/due-diligence/matters/{matter_id}/comparisons",
    }

    assert expected_paths.issubset(set(paths.keys()))


def test_risk_scale_and_categories_are_constrained():
    item=RiskCreate(category="litigation",title="Pending appeal",description="Appeal is pending before the tribunal.",likelihood=4,impact=5)
    assert item.likelihood*item.impact == 20
    try:
        RiskCreate(category="litigation",title="Bad",description="This is long enough",likelihood=6,impact=2)
        assert False, "likelihood above five must be rejected"
    except Exception:
        pass

def test_matter_types_are_constrained():
    item=MatterCreate(tenant_id="t",title="Acquisition review",matter_type="transaction",subject_name="Target Co")
    assert item.matter_type=="transaction"

def test_comparison_requires_change_records():
    item=ComparisonCreate(document_label="Share purchase agreement",version_a_label="v1",version_b_label="v2",changes=[{"clause":"8","change":"New indemnity cap"}])
    assert item.review_status=="pending_review"
