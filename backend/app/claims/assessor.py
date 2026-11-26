"""Conservative lexical claim/evidence assessment.

Scores identify candidate textual overlap only. They do not determine legal entailment.
"""
from __future__ import annotations
import re

_STOP = {
    "the","and","for","with","from","that","this","there","their","into","under",
    "after","before","where","when","which","what","does","shall","will","would",
    "could","should","must","may","can","not","are","was","were","has","have",
    "had","been","being","a","an","of","to","in","on","by","as","or","is","it",
    "its","at","be","than","then","such","also","any","all","each","both"
}

def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{2,}", (text or "").lower()) if t not in _STOP}

def assess_claim(claim: str, evidence: list[dict]) -> dict:
    """Rank supplied passages by lexical overlap and return cautious review statuses."""
    claim_terms = _tokens(claim)
    if not claim_terms:
        return {
            "assessment_status": "insufficient_claim_terms",
            "evidence_assessments": [],
            "limitations": ["The claim did not contain enough searchable terms."],
        }
    rows = []
    for item in evidence:
        body = str(item.get("text") or "")
        evidence_terms = _tokens(body)
        overlap = claim_terms & evidence_terms
        precision = len(overlap) / len(claim_terms)
        recall = len(overlap) / len(evidence_terms) if evidence_terms else 0.0
        # A balanced lexical score; deliberately not described as entailment.
        score = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        if precision >= 0.60 and len(overlap) >= 3:
            status = "candidate_support"
        elif precision >= 0.25 and len(overlap) >= 2:
            status = "weak_overlap"
        else:
            status = "no_material_overlap"
        rows.append({
            "evidence_id": item.get("evidence_id"),
            "source_label": item.get("source_label"),
            "locator": item.get("locator"),
            "page": item.get("page"),
            "status": status,
            "overlap_score": round(score, 4),
            "claim_term_coverage": round(precision, 4),
            "matched_terms": sorted(overlap),
            "excerpt": body[:1200],
        })
    rows.sort(key=lambda r: (r["claim_term_coverage"], r["overlap_score"]), reverse=True)
    if any(r["status"] == "candidate_support" for r in rows):
        overall = "candidate_support"
    elif any(r["status"] == "weak_overlap" for r in rows):
        overall = "weak_overlap"
    else:
        overall = "no_support_found"
    return {
        "assessment_status": overall,
        "evidence_assessments": rows,
        "limitations": [
            "This is a deterministic lexical-overlap screen, not a legal entailment or contradiction model.",
            "A candidate-support result requires human review of the complete source passage and surrounding context.",
            "No result means only that the supplied passages did not show sufficient lexical overlap; it does not prove the claim is false.",
            "The service assesses only the evidence passages supplied in this request; it does not independently retrieve or authenticate them.",
        ],
    }
