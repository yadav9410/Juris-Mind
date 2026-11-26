from app.research.planner import build_research_plan, suggest_sub_questions


def test_planner_preserves_original_question_and_splits_explicit_clauses():
    question = "What is the legal test for bail?; How is it applied by the Supreme Court?"
    plan = build_research_plan(question)
    assert plan.original_question == question
    assert len(plan.sub_questions) == 2
    assert plan.planning_method == "rule_based_clause_split"


def test_user_supplied_sub_questions_are_used_in_order_and_deduplicated():
    plan = build_research_plan(
        "Main research question about bail standards",
        ["Bail under statute", "Bail under statute", "Supreme Court treatment"],
    )
    assert plan.sub_questions == ["Bail under statute", "Supreme Court treatment"]
    assert plan.planning_method == "user_supplied"


def test_planner_caps_number_of_sub_questions():
    supplied = [f"Research issue number {i}" for i in range(12)]
    assert len(suggest_sub_questions("A sufficiently detailed legal question", supplied)) == 8
