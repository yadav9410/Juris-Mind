from pathlib import Path

import pytest

from scripts.ingest_document import infer_content_type


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("act.pdf", "application/pdf"),
        ("judgment.html", "text/html"),
        ("notice.HTM", "text/html"),
    ],
)
def test_infer_content_type(filename, expected):
    assert infer_content_type(Path(filename)) == expected


def test_reject_unsupported_extension():
    with pytest.raises(ValueError, match="PDF or HTML"):
        infer_content_type(Path("archive.docx"))
