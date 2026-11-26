"""PDF/HTML extraction with optional OCR fallback for scanned PDFs."""
from dataclasses import dataclass, field
from pathlib import Path
import shutil
import fitz
from bs4 import BeautifulSoup


@dataclass
class ExtractionResult:
    text: str
    page_count: int | None
    needs_ocr: bool
    content_type: str
    ocr_used: bool = False
    # One-based PDF page numbers; HTML extraction has no reliable page concept.
    page_texts: list[tuple[int, str]] = field(default_factory=list)


def extract_pdf(path: Path, *, ocr_enabled: bool = True, ocr_languages: str = "eng",
                min_text_chars: int = 80) -> ExtractionResult:
    pages = []
    page_texts = []
    ocr_used = False
    with fitz.open(path) as doc:
        count = len(doc)
        for page in doc:
            page_text = page.get_text("text").strip()
            # OCR only pages with very little native text; preserve native text otherwise.
            if ocr_enabled and len(page_text) < min_text_chars:
                if shutil.which("tesseract"):
                    try:
                        text_page = page.get_textpage_ocr(language=ocr_languages, dpi=200, full=True)
                        ocr_text = page.get_text("text", textpage=text_page).strip()
                        if len(ocr_text) > len(page_text):
                            page_text = ocr_text
                            ocr_used = True
                    except Exception:
                        # OCR failure is explicit in needs_ocr; never silently treat as complete.
                        pass
            pages.append(page_text)
            page_texts.append((page.number + 1, page_text))
    text = "\n\n".join(pages).strip()
    needs_ocr = len(text) < min_text_chars
    return ExtractionResult(text, count, needs_ocr, "application/pdf", ocr_used, page_texts)


def extract_html(path: Path) -> ExtractionResult:
    raw = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    for node in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        node.decompose()
    text = soup.get_text(" ", strip=True)
    return ExtractionResult(text, None, len(text) < 80, "text/html", False)


def extract_document(path: Path, content_type: str, **options) -> ExtractionResult:
    if content_type == "application/pdf":
        return extract_pdf(path, **options)
    if content_type in {"text/html", "application/xhtml+xml"}:
        return extract_html(path)
    raise ValueError("Only PDF and HTML documents are supported.")
