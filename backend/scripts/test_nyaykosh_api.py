"""Live, read-only smoke test for Nyaykosh's publicly demonstrated DPDP API.

Run from backend/: python scripts/test_nyaykosh_api.py
No API key is required. Network/TLS failures are reported without weakening TLS.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.sources.nyaykosh import NyaykoshClient, NyaykoshError  # noqa: E402


def main() -> int:
    client = NyaykoshClient()
    try:
        result = client.get_law_with_penalties("dpdp-2023")
    except NyaykoshError as exc:
        print(json.dumps({"provider": "Nyaykosh", "live_test": "failed", "error": str(exc)}, indent=2))
        return 1
    law_data = result["law"]["data"]
    print(json.dumps({
        "provider": "Nyaykosh (NeGD Law as Code)",
        "live_test": "passed",
        "law_endpoint": result["law"]["endpoint"],
        "law_http_status": result["law"]["http_status"],
        "law_top_level_keys": sorted(law_data.keys()) if isinstance(law_data, dict) else None,
        "law_title": law_data.get("title") if isinstance(law_data, dict) else None,
        "law_id": law_data.get("id") if isinstance(law_data, dict) else None,
        "sections_count": law_data.get("sections") if isinstance(law_data, dict) else None,
        "penalties_status": result["penalties"]["status"],
        "penalties_endpoint": result["penalties"]["endpoint"],
        "penalties_count": len(result["penalties"]["data"]) if isinstance(result["penalties"]["data"], list) else None,
        "verification_status": result["verification_status"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
