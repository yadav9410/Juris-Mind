"""Conservative rule-based extraction for common Indian legal citations.

This module identifies citation-shaped strings; it does not certify their truth.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class CitationCandidate:
    citation_text: str
    citation_type: str
    start_offset: int
    end_offset: int
    normalized: dict

_CASE_PATTERNS = [
    ("neutral", re.compile(r"\b(?:19|20)\d{2}\s+INSC\s+\d{1,5}\b", re.I)),
    ("scc", re.compile(r"\(\s*(?:19|20)\d{2}\s*\)\s*\d{1,2}\s*SCC\s+\d{1,4}\b", re.I)),
    ("air", re.compile(r"\bAIR\s+(?:19|20)\d{2}\s+(?:SC| All| Allahabad| Del| Bom| Cal| Mad| Ker| P&H|Raj)\s+\d{1,5}\b", re.I)),
    ("scr", re.compile(r"\b(?:19|20)\d{2}\s+\(\d+\)\s+SCR\s+\d{1,4}\b", re.I)),
]
_STATUTE_PATTERN = re.compile(
    r"\b(?:Section|Sections|Sec\.?|Article|Articles|Art\.?|Rule|Rules)\s+"
    r"\d+[A-Za-z]?(?:\s*\(\s*\d+[A-Za-z]?\s*\))*(?:\s*\(\s*[a-z]\s*\))?",
    re.I,
)

def normalize_citation(text: str, citation_type: str) -> dict:
    cleaned = re.sub(r"\s+", " ", text).strip().rstrip(".,;")
    if citation_type == "statutory":
        m = re.match(r"(?P<kind>Sections?|Secs?\.?|Articles?|Arts?\.?|Rules?)\s+(?P<ref>.+)", cleaned, re.I)
        return {"kind": (m.group("kind").lower().rstrip(".") if m else "provision"),
                "provision_ref": cleaned}
    if citation_type == "neutral":
        m = re.search(r"((?:19|20)\d{2})\s+INSC\s+(\d+)", cleaned, re.I)
        return {"year": int(m.group(1)), "court_code": "INSC", "number": int(m.group(2)), "canonical": f"{m.group(1)} INSC {m.group(2)}"} if m else {"canonical": cleaned}
    if citation_type == "scc":
        m = re.search(r"\(?((?:19|20)\d{2})\)?\s*(\d+)\s*SCC\s+(\d+)", cleaned, re.I)
        return {"year": int(m.group(1)), "reporter": "SCC", "volume": int(m.group(2)), "page": int(m.group(3)), "canonical": f"({m.group(1)}) {m.group(2)} SCC {m.group(3)}"} if m else {"canonical": cleaned}
    if citation_type == "air":
        m = re.search(r"AIR\s+((?:19|20)\d{2})\s+([A-Z&. ]+?)\s+(\d+)", cleaned, re.I)
        return {"year": int(m.group(1)), "reporter": "AIR", "court": m.group(2).strip(), "page": int(m.group(3)), "canonical": cleaned} if m else {"canonical": cleaned}
    return {"canonical": cleaned}

def extract_citations(text: str) -> list[CitationCandidate]:
    """Extract citations while preserving exact source offsets and source wording."""
    if not isinstance(text, str) or not text.strip():
        return []
    found = []
    for citation_type, pattern in _CASE_PATTERNS:
        for match in pattern.finditer(text):
            found.append((match.start(), match.end(), citation_type, match.group(0)))
    for match in _STATUTE_PATTERN.finditer(text):
        found.append((match.start(), match.end(), "statutory", match.group(0)))
    # Prefer the longest candidate when patterns overlap.
    found.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    selected = []
    last_end = -1
    for start, end, kind, raw in found:
        if start < last_end:
            continue
        selected.append(CitationCandidate(raw, kind, start, end, normalize_citation(raw, kind)))
        last_end = end
    return selected
