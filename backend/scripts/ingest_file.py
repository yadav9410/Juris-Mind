"""Run: python scripts/ingest_file.py <file> --type application/pdf"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ingestion.service import ingest_file

parser = argparse.ArgumentParser(description="Ingest one PDF or HTML file into the JurisMind staging pipeline.")
parser.add_argument("file")
parser.add_argument("--type", required=True, dest="content_type", help="application/pdf or text/html")
args = parser.parse_args()
result = ingest_file(args.file, filename=Path(args.file).name, content_type=args.content_type)
print(json.dumps(result, indent=2))
