from app.api.reasoning import CreateWorkspace, Issue, Argument, ReviewUpdate

def test_reasoning_workspace_accepts_linked_issue_and_argument_map():
    payload = CreateWorkspace(
        tenant_id="tenant-1", title="Contract dispute", fact_summary="A concise factual summary of the dispute.",
        linked_snapshot_id="snapshot-1", linked_assessment_ids=["assessment-1"],
        issues=[Issue(issue="Whether the termination was contractually valid", legal_test_or_elements=["Notice requirement"], facts_supporting=["Notice was sent"], evidence_refs=["doc:1:p2"])],
        arguments=[Argument(issue_index=0, side="claimant", proposition="Termination was invalid", supporting_reasons=["Notice period was insufficient"], evidence_refs=["doc:1:p2"], counterarguments=["Contract permitted immediate termination"])],
    )
    assert payload.arguments[0].issue_index == 0
    assert payload.issues[0].status == "open"

def test_review_status_is_restricted():
    assert ReviewUpdate(review_status="in_review", reviewer_notes="Check authorities").review_status == "in_review"
