"""Curated official Indian legal research portals.

Portal presence does not imply a supported machine-search API. Search URLs are
entry points for human review until a source adapter is separately validated.
"""
from __future__ import annotations

SOURCES = [
    {
        "source_id": "india_code", "name": "India Code",
        "url": "https://indiacode.gov.in/",
        "search_url": "https://indiacode.gov.in/",
        "tier": "primary", "category": "legislation",
        "source_types": ["central_act", "state_act", "subordinate_legislation"],
        "coverage": ["india", "uttar_pradesh"],
        "automation": "portal_review_required",
        "notes": "Official Legislative Department repository; verify the current consolidated text against the relevant Gazette publication and amendments.",
    },
    {
        "source_id": "egazette_india", "name": "e-Gazette of India",
        "url": "https://egazette.gov.in/",
        "search_url": "https://egazette.gov.in/",
        "tier": "primary", "category": "gazette",
        "source_types": ["act", "notification", "rule", "order"],
        "coverage": ["india"], "automation": "portal_review_required",
        "notes": "Official Gazette publication; publication details and document authenticity must be retained.",
    },
    {
        "source_id": "supreme_court_scr", "name": "Supreme Court Reports (SCR)",
        "url": "https://scr.sci.gov.in/scrsearch/",
        "search_url": "https://scr.sci.gov.in/scrsearch/",
        "tier": "primary", "category": "judgment",
        "source_types": ["reportable_judgment", "supreme_court_report"],
        "coverage": ["india"], "automation": "portal_review_required",
        "notes": "Official SCR/e-SCR portal. Use the court's published judgment/report, not a search snippet.",
    },
    {
        "source_id": "allahabad_elegalix", "name": "Allahabad High Court eLegalix",
        "url": "https://elegalix.allahabadhighcourt.in/",
        "search_url": "https://elegalix.allahabadhighcourt.in/",
        "tier": "primary", "category": "judgment",
        "source_types": ["judgment", "order"],
        "coverage": ["uttar_pradesh", "allahabad", "lucknow_bench"],
        "automation": "portal_review_required",
        "notes": "Official Allahabad High Court and Lucknow Bench judgment information system.",
    },
    {
        "source_id": "ecourts_judgments", "name": "Judgments and Orders Search Portal",
        "url": "https://judgments.ecourts.gov.in/pdfsearch/index.php",
        "search_url": "https://judgments.ecourts.gov.in/pdfsearch/index.php",
        "tier": "primary", "category": "judgment",
        "source_types": ["high_court_judgment", "order"],
        "coverage": ["india", "high_courts"],
        "automation": "manual_captcha_portal",
        "notes": "Official e-Committee portal. Interactive CAPTCHA means automated CAPTCHA solving or bypass is not supported.",
    },
]

SOURCE_BY_ID = {item["source_id"]: item for item in SOURCES}
