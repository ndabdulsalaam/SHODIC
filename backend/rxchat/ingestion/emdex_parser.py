"""Parser for licensed EMDEX source uploads."""

from __future__ import annotations

from pathlib import Path

from .base import DocumentChunk, chunk_text, extract_text
from .storage import save_clean_record


def parse_emdex(raw) -> tuple[str, list[DocumentChunk]]:
    """Extract text from a single RawData upload."""
    path = Path(raw.file.path)
    text = extract_text(path)
    title = f"EMDEX - {path.stem}"

    clean = save_clean_record(
        "emdex",
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
    title = f"EMDEX - {Path(path_name).stem}" if path_name else "EMDEX"
    chunks = []
    for idx, chunk in enumerate(chunk_text(text), start=1):
        chunks.append(DocumentChunk(
            id=f"emdex:{clean.pk}:{idx}",
            text=f"{title}\n\n{chunk}",
            source=title,
            source_type="emdex",
            record_id=str(clean.source_id),
            status="active",
            is_active=True,
            effective_date="",
            metadata={"filename": path_name, "drug_name": title, "category": "EMDEX"},
        ))
    return chunks
