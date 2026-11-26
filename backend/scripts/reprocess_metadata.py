
"""Command-line entry point for metadata reprocessing."""

import json
import sys

from app.ingestion.metadata_reprocessor import reprocess_metadata


if len(sys.argv) != 2:
    print(
        "Usage: python scripts/reprocess_metadata.py JOB_ID"
    )
    raise SystemExit(2)

try:
    result = reprocess_metadata(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as exc:
    print(f"Metadata reprocessing failed: {exc}")
    raise SystemExit(1)
