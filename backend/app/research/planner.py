
"""Conservative, deterministic research-plan suggestions.

This is a transparent baseline planner, not an LLM agent. It preserves the
user's question and only creates additional queries from explicit clauses.
Users may provide their own sub-questions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchPlan:
    original_question: str
    sub_questions: list[str]
    planning_method: str
    planning_notice: str


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n;,.?-")


def suggest_sub_questions(
    question: str,
    supplied: list[str] | None = None,
) -> list[str]:
    """Return bounded, de-duplicated research queries in stable order."""

    if supplied:
        candidates = [
            _clean(item)
            for item in supplied
            if item and _clean(item)
        ]
    else:
        # Split only at actual question marks, semicolons or newlines.
        candidates = [
            _clean(part)
            for part in re.split(r"[?;\n]+", question)
            if _clean(part)
        ]

        # Split explicit connecting clauses only when no clear split exists.
        if len(candidates) <= 1:
            candidates = [
                _clean(part)
                for part in re.split(
                    r"\s+(?:and also|as well as)\s+",
                    question,
                    flags=re.I,
                )
                if _clean(part)
            ]

        # Preserve the complete question if no meaningful split exists.
        if len(candidates) <= 1:
            candidates = [_clean(question)]

    output: list[str] = []
    seen: set[str] = set()

    for item in candidates:
        key = item.casefold()

        if len(item) < 3 or key in seen:
            continue

        seen.add(key)
        output.append(item[:500])

        if len(output) == 8:
            break

    return output or [_clean(question)[:500]]


def build_research_plan(
    question: str,
    supplied_sub_questions: list[str] | None = None,
) -> ResearchPlan:
    """Create an explainable plan without claiming legal analysis."""

    sub_questions = suggest_sub_questions(
        question,
        supplied_sub_questions,
    )

    return ResearchPlan(
        original_question=question.strip(),
        sub_questions=sub_questions,
        planning_method=(
            "user_supplied"
            if supplied_sub_questions
            else "rule_based_clause_split"
        ),
        planning_notice=(
            "Planning suggestions are deterministic and do not constitute "
            "legal analysis. Review and refine the sub-questions before "
            "relying on research."
        ),
    )
