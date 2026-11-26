
"""Conservative legal structure detection and legal-aware chunking.

Detected labels are navigational hints, not a substitute for checking
the original source.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re


@dataclass
class LegalChunk:
    ordinal: int
    chunk_type: str
    locator: str | None
    heading: str | None
    text: str
    page_start: int | None = None
    page_end: int | None = None


# Recognizes common Indian legal document labels:
# Section 19, Sec. 19, Article 14, Rule 5, Regulation 3, etc.
SECTION_RE = re.compile(
    r"^\s*((?:section|sec\.|article|art\.|rule|regulation)\s+"
    r"[0-9A-Za-z]+(?:\([0-9A-Za-z]+\))*(?:[A-Z])?)"
    r"(?:\s*[.\-–:]\s*(.*))?\s*$",
    re.IGNORECASE,
)

JUDGMENT_PARA_RE = re.compile(
    r"^\s*\(?(\d{1,4})\)?[.)]\s+(.+)$"
)

SCHEDULE_RE = re.compile(
    r"^\s*(first|second|third|fourth|fifth|sixth|seventh|"
    r"eighth|ninth|tenth)\s+schedule\b",
    re.IGNORECASE,
)


def _split_oversize(
    text: str,
    max_chars: int,
    overlap: int,
) -> list[str]:
    """Split long passages near paragraph boundaries with bounded overlap."""
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    result: list[str] = []
    current = ""

    for paragraph in paragraphs:
        while len(paragraph) > max_chars:
            if current:
                result.append(current)
                current = ""

            cut = paragraph.rfind(" ", 0, max_chars)

            if cut < max_chars // 2:
                cut = max_chars

            result.append(paragraph[:cut].strip())
            paragraph = paragraph[max(0, cut - overlap):].strip()

        candidate = (
            f"{current}\n\n{paragraph}".strip()
            if current
            else paragraph
        )

        if len(candidate) > max_chars and current:
            result.append(current)
            current = paragraph
        else:
            current = candidate

    if current:
        result.append(current)

    return result


def structure_legal_text(
    text: str,
    document_type: str,
    *,
    max_chars: int = 3500,
    overlap: int = 250,
) -> list[LegalChunk]:
    """Create legal-aware chunks while retaining detected headings and locators."""

    if max_chars < 500 or overlap < 0 or overlap >= max_chars:
        raise ValueError(
            "Use max_chars >= 500 and 0 <= overlap < max_chars."
        )

    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.splitlines()

    # Each block retains its own type, locator, heading and body.
    blocks: list[tuple[str, str | None, str | None, str]] = []

    current_type = (
        "preamble"
        if document_type in {"act", "rules", "notification"}
        else "body"
    )
    current_locator: str | None = None
    current_heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer

        value = "\n".join(buffer).strip()

        if value:
            blocks.append(
                (
                    current_type,
                    current_locator,
                    current_heading,
                    value,
                )
            )

        buffer = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            buffer.append("")
            continue

        section = SECTION_RE.match(stripped)
        schedule = SCHEDULE_RE.match(stripped)

        paragraph = (
            JUDGMENT_PARA_RE.match(stripped)
            if document_type == "judgment"
            else None
        )

        if section or schedule or paragraph:
            flush()

            if section:
                current_type = "provision"
                current_locator = section.group(1).strip()
                current_heading = (
                    section.group(2).strip()
                    if section.group(2)
                    else None
                )
                buffer.append(stripped)

            elif schedule:
                current_type = "schedule"
                current_locator = stripped
                current_heading = None
                buffer.append(stripped)

            else:
                current_type = "judgment_paragraph"
                current_locator = paragraph.group(1)
                current_heading = None
                buffer.append(stripped)

        else:
            buffer.append(line)

    flush()

    chunks: list[LegalChunk] = []
    ordinal = 0

    for kind, locator, heading, block in blocks:
        pieces = _split_oversize(block, max_chars, overlap)

        for piece in pieces:
            ordinal += 1

            chunks.append(
                LegalChunk(
                    ordinal=ordinal,
                    chunk_type=kind,
                    locator=locator,
                    heading=heading,
                    text=piece,
                )
            )

    return chunks


def chunks_as_dicts(chunks: list[LegalChunk]) -> list[dict]:
    """Convert legal chunks into dictionaries."""
    return [asdict(chunk) for chunk in chunks]
