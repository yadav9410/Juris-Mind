"""First-stage ingestion: validate, hash, preserve original, extract and track."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import shutil
import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.ingestion import IngestionJob
from app.ingestion.extractors import extract_document
from app.ingestion.validation import validate_file, sha256_file
from app.ingestion.classifier import classify_legal_text
from app.ingestion.structuring import structure_legal_text, LegalChunk
from app.models.ingestion import IngestionChunk


def ingest_file(
    source_path: str | Path,
    *,
    filename: str,
    content_type: str,
    database_url: str | None = None,
    source_name: str | None = None,
    source_url: str | None = None,
    source_class: str = "unverified",
) -> dict:
    """Ingest one PDF/HTML file. Corpus writes use the dedicated ingest DB role."""
    settings = get_settings()
    db_url = database_url or settings.ingestion_database_url
    if not db_url:
        raise RuntimeError("INGESTION_DATABASE_URL must point to the jurismind_ingest role.")
    path = Path(source_path)
    detected_type = validate_file(path, filename, content_type)
    digest = sha256_file(path)

    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    storage_root = Path(settings.ingestion_storage_dir).resolve()
    originals = storage_root / "originals"
    extracted_dir = storage_root / "extracted"
    originals.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    job_id = str(uuid4())
    suffix = ".pdf" if detected_type == "application/pdf" else ".html"
    original_key = f"{job_id}{suffix}"
    original_path = originals / original_key
    text_path = extracted_dir / f"{job_id}.txt"

    try:
        with Session.begin() as db:
            existing = db.scalar(select(IngestionJob).where(
                IngestionJob.content_sha256 == digest,
                IngestionJob.status.in_(["extracted", "needs_ocr"]),
            ))
            if existing:
                return {"job_id": existing.id, "status": "duplicate", "sha256": digest}
            job = IngestionJob(
                id=job_id, filename=Path(filename).name[:500],
                content_sha256=digest, content_type=detected_type, status="received",
            )
            db.add(job)
        shutil.copyfile(path, original_path)
        result = extract_document(
            original_path, detected_type,
            ocr_enabled=settings.ocr_enabled,
            ocr_languages=settings.ocr_languages,
            min_text_chars=settings.ocr_min_text_chars,
        )
        classification = classify_legal_text(result.text, filename)
        if result.needs_ocr:
            status = "needs_ocr"
        else:
            status = "extracted"
        text_path.write_text(result.text, encoding="utf-8")
        with Session.begin() as db:
            job = db.get(IngestionJob, job_id)
            job.status = status
            job.storage_key = str(original_path.relative_to(storage_root))
            job.extracted_text_key = str(text_path.relative_to(storage_root))
            job.page_count = result.page_count
            job.ocr_used = result.ocr_used
            job.classification_json = json.dumps(classification, ensure_ascii=False)
            job.metadata_json = json.dumps({
                **classification,
                "metadata_origin": "automated_candidate_extraction",
                "verified": False,
            }, ensure_ascii=False)
            job.metadata_review_status = "pending"
            job.source_name = (source_name or "")[:200] or None
            job.source_url = source_url
            job.source_class = source_class if source_class in {"primary", "secondary", "unverified"} else "unverified"
            job.completed_at = datetime.now(timezone.utc)
            # Store legal-aware chunks as staging records; they are not yet published
            # into the shared legal corpus or exposed as verified legal authority.
            document_type = classification.get("document_type", "unknown")
            chunks = []
            if result.page_texts:
                # Structure each PDF page independently so every stored chunk has
                # a defensible one-based source page. Cross-page passages remain
                # separate; this is safer than guessing page boundaries later.
                ordinal = 0
                for page_number, page_text in result.page_texts:
                    for page_chunk in structure_legal_text(page_text, document_type):
                        ordinal += 1
                        chunks.append(LegalChunk(
                            ordinal=ordinal,
                            chunk_type=page_chunk.chunk_type,
                            locator=page_chunk.locator,
                            heading=page_chunk.heading,
                            text=page_chunk.text,
                            page_start=page_number,
                            page_end=page_number,
                        ))
            else:
                # HTML has no intrinsic page numbering; leave page references null.
                chunks = structure_legal_text(result.text, document_type)
            for chunk in chunks:
                db.add(IngestionChunk(
                    job_id=job_id,
                    ordinal=chunk.ordinal,
                    chunk_type=chunk.chunk_type,
                    locator=chunk.locator,
                    heading=chunk.heading,
                    body_text=chunk.text,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                ))
        return {
            "job_id": job_id, "status": status, "sha256": digest,
            "content_type": detected_type, "page_count": result.page_count,
            "storage_key": str(original_path.relative_to(storage_root)),
            "extracted_text_key": str(text_path.relative_to(storage_root)),
            "character_count": len(result.text), "ocr_used": result.ocr_used,
            "classification": classification,
            "chunk_count": len(chunks),
        }
    except Exception as exc:
        # Best-effort persisted failure record; never mark a failed file as indexed/published.
        try:
            with Session.begin() as db:
                job = db.get(IngestionJob, job_id)
                if job:
                    job.status = "failed"
                    job.error_code = type(exc).__name__[:80]
                    job.error_message = str(exc)[:2000]
                    job.completed_at = datetime.now(timezone.utc)
        except Exception:
            pass
        raise
    finally:
        engine.dispose()
