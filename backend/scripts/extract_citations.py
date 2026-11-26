
"""Print citation candidates from a UTF-8 text file."""

import argparse
import json
import sys
from pathlib import Path

# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.citations.extractor import extract_citations


def main():
    parser = argparse.ArgumentParser(
        description="Extract citation-shaped text from a file."
    )
    parser.add_argument("file", help="Path to a UTF-8 text file")
    args = parser.parse_args()

    text = Path(args.file).read_text(encoding="utf-8")

    results = [
        {
            "citation_text": item.citation_text,
            "citation_type": item.citation_type,
            "start_offset": item.start_offset,
            "end_offset": item.end_offset,
            "normalized": item.normalized,
        }
        for item in extract_citations(text)
    ]

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
