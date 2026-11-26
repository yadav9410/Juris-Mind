"""Conservative legal-document classification; outputs are unverified candidates."""
from __future__ import annotations
import re
from datetime import date, datetime

MONTH_PATTERN = (
    r"January|February|March|April|May|June|July|August|September|"
    r"October|November|December"
)
PATTERNS = [
    ("judgment", r"\b(judg(?:e)?ment|court\s+held|appeal\s+dismissed|petition\s+allowed|special\s+leave\s+petition|civil\s+appeal\s+no\.?|criminal\s+appeal\s+no\.?)\b"),
    ("act", r"\b(an\s+act\s+to|be\s+it\s+enacted|the\s+following\s+act|act\s+no\.?\s*\d+|the\s+[a-z ]+code,?\s*(?:18|19|20)\d{2})\b"),
    ("regulations", r"\b(regulations?\s*,?\s*(?:18|19|20)\d{2}|in exercise of the powers conferred by.*?regulations?)\b"),
    ("rules", r"\b(central\s+rules|state\s+rules|rules?\s*,?\s*20\d{2}|in\s+exercise\s+of\s+the\s+powers\s+conferred)\b"),
    ("notification", r"\b(notification|s\.?\s*o\.?\s*\d+|g\.?\s*s\.?\s*r\.?\s*\d+)\b"),
    ("order", r"\b(operative\s+order|interim\s+order\s+dated|final\s+order\s+dated|order\s+pronounced\s+on|ordered\s+accordingly)\b"),
]

def _extract_title(text: str) -> str | None:
    excluded = ("page ", "www.", "http://", "https://", "downloaded", "printed")
    for raw in (text or "").splitlines()[:40]:
        line = re.sub(r"\s+", " ", raw).strip(" \t|:-")
        if 8 <= len(line) <= 250 and not any(x in line.lower() for x in excluded) and len(re.findall(r"[A-Za-z]", line)) >= 5:
            return line
    return None

def _extract_decision_date(text: str) -> str | None:
    sample = (text or "")[:200_000]
    m = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?[ ./-]+({MONTH_PATTERN})[, ]+(20\d{{2}})\b", sample, re.I)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y").date().isoformat()
        except ValueError:
            pass
    m = re.search(r"\b(0?[1-9]|[12]\d|3[01])[./-](0?[1-9]|1[0-2])[./-](20\d{2})\b", sample)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            pass
    return None

def classify_legal_text(text: str, filename: str = "") -> dict:
    sample = (text or "")[:200_000]
    lower = sample.lower()
    scores = {label: len(re.findall(pattern, lower, re.I)) for label, pattern in PATTERNS}
    filename_lower = (filename or "").lower()
    # Strong title/filename signals prevent legislation named "... Code, YYYY"
    # from being mistaken for an order merely because boilerplate says "ordered".
    if re.search(r"\b(act|code)\s*,?\s*(18|19|20)\d{2}\b", filename_lower) or re.search(r"\b(act|code)\s*,?\s*(18|19|20)\d{2}\b", lower[:8000]):
        scores["act"] = scores.get("act", 0) + 8
    if re.search(r"\bjudgment|\border\b", filename_lower):
        scores["judgment"] = scores.get("judgment", 0) + int("judgment" in filename_lower)
        scores["order"] = scores.get("order", 0) + int("order" in filename_lower)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if not ranked or ranked[0][1] == 0 or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
        document_type = "unknown"
    else:
        document_type = ranked[0][0]

    year_match = re.search(r"\b(18|19|20)\d{2}\b", sample[:12_000])
    year_candidate = int(year_match.group(0)) if year_match else None
    court_candidate = None
    for pattern, value in [
        (r"\bsupreme\s+court\s+of\s+india\b", "Supreme Court of India"),
        (r"\ballahabad\s+high\s+court\b|\bhigh\s+court\s+of\s+judicature\s+at\s+allahabad\b", "Allahabad High Court"),
    ]:
        if re.search(pattern, lower):
            court_candidate = value
            break

    if court_candidate == "Supreme Court of India" or re.search(r"\b(government\s+of\s+india|india)\b", lower):
        jurisdiction_candidate = "India"
    elif court_candidate == "Allahabad High Court" or re.search(r"\b(uttar\s+pradesh|allahabad|prayagraj)\b", lower):
        jurisdiction_candidate = "Uttar Pradesh, India"
    else:
        jurisdiction_candidate = None

    citation = re.search(r"\b(20\d{2})\s+INSC\s+(\d+)\b", sample, re.I)
    decision_date = _extract_decision_date(sample)
    if decision_date:
        year_candidate = int(decision_date[:4])
    top = max(scores.values(), default=0)
    second = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
    return {
        "document_type": document_type,
        "title_candidate": _extract_title(sample),
        "year_candidate": year_candidate,
        "court_candidate": court_candidate,
        "jurisdiction_candidate": jurisdiction_candidate,
        "decision_date_candidate": decision_date,
        "neutral_citation_candidate": f"{citation.group(1)} INSC {citation.group(2)}" if citation else None,
        "classification_confidence": "medium" if document_type != "unknown" and top >= 3 and top > second else "low",
        "classification_scores": scores,
        "requires_human_review": True,
        "filename_hint": filename or None,
    }
