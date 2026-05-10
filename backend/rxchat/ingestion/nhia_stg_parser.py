"""Parser for NHIA Standard Treatment Guidelines."""

from __future__ import annotations

from pathlib import Path

from .base import DocumentChunk, chunk_text, extract_text
from .storage import save_clean_record

TITLE = "Nigeria Standard Treatment Guidelines"


def parse_nhia_stg(raw) -> tuple[str, list[DocumentChunk]]:
    """Extract text from a single RawData upload."""
    path = Path(raw.file.path)
    text = extract_text(path)

    clean = save_clean_record(
        "nhia_stg",
        f"upload:{raw.pk}",
        raw_text=text,
        file_name=raw.file.name,
        raw_id=raw.pk,
    )

    return text, build_chunks_from_clean(clean)


def build_chunks_from_clean(clean) -> list[DocumentChunk]:
    """Build chunks from an accepted CleanData record (called by ingest_drugs)."""
    text = clean.raw_text
    path_name = clean.file_name or ""
    chunks = []
    for idx, chunk in enumerate(chunk_text(text), start=1):
        chunks.append(DocumentChunk(
            id=f"nhia_stg:{clean.pk}:{idx}",
            text=f"{TITLE}\n\n{chunk}",
            source=TITLE,
            source_type="nhia_stg",
            record_id=str(clean.source_id),
            status="active",
            is_active=True,
            metadata={"filename": path_name, "drug_name": TITLE, "category": "NHIA STG"},
        ))
    return chunks
