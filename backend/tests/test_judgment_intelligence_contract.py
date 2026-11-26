from datetime import date
from app.api.judgment_intelligence import JudgmentAnalysisCreate, ReviewUpdate

def test_judgment_analysis_contract_accepts_structured_record():
    payload = JudgmentAnalysisCreate(
        tenant_id="tenant-1", ingestion_job_id="job-1", source_chunk_id="chunk-1",
        case_title="Example v Example", decision_date=date(2024, 1, 1),
        facts=["Fact one"], issues=["Whether issue one arises"],
        holdings=["Holding one"], cited_authorities=["(2020) 1 SCC 1"],
    )
    assert payload.case_title == "Example v Example"
    assert payload.issues == ["Whether issue one arises"]

def test_review_status_is_restricted():
    assert ReviewUpdate(review_status="reviewed").review_status == "reviewed"
