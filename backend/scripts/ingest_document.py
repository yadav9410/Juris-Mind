"""Run one trusted local PDF/HTML ingestion job.

This script uses INGESTION_DATABASE_URL (jurismind_ingest), never the API role.
Run it from the project root in an activated Python virtual environment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from app.ingestion.service import ingest_file


def infer_content_type(path: Path) -> str:
    """Infer the supported MIME type from a local filename extension."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".html", ".htm"}:
        return "text/html"
    raise ValueError("Unsupported file type. Provide a PDF or HTML file.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest one PDF/HTML file into JurisMind's staged legal corpus."
    )
    parser.add_argument("file", help="Path to a local PDF or HTML file")
    parser.add_argument(
        "--content-type",
        choices=["application/pdf", "text/html"],
        help="Optional MIME type override; normally inferred from the extension.",
    )
    parser.add_argument("--source-name", help="Publisher or website name (provenance only)")
    parser.add_argument("--source-url", help="Exact source URL, if known")
    parser.add_argument("--source-class", choices=["primary", "secondary", "unverified"], default="unverified")
    args = parser.parse_args()

    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        parser.error(f"File not found: {path}")

    try:
        content_type = args.content_type or infer_content_type(path)
        result = ingest_file(
            path,
            filename=path.name,
            content_type=content_type,
            source_name=args.source_name, source_url=args.source_url, source_class=args.source_class,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"Ingestion not completed: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            f"Ingestion failed ({type(exc).__name__}): {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
