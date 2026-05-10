"""Parser for Nigeria Essential Medicines List PDFs.

Returns plain extracted text per file.  Called by the ``parse_data``
management command which stores the output in CleanData.
"""

from __future__ import annotations

from pathlib import Path

from .base import DocumentChunk, chunk_text, extract_text, utc_timestamp
from .storage import replace_chunks, save_clean_record


def parse_neml(raw) -> tuple[str, list[DocumentChunk]]:
    """Extract text from a single RawData upload and return chunks.

    Args:
        raw: A ``RawData`` instance.

    Returns:
        (plain_text, list[DocumentChunk])
    """
    path = Path(raw.file.path)
    text = extract_text(path)
    title = _title_for(path)

    clean = save_clean_record(
        "neml",
        f"upload:{raw.pk}",
        raw_text=text,
        file_name=raw.file.name,
        raw_id=raw.pk,
    )

    record_chunks = []
    for idx, chunk in enumerate(chunk_text(text), start=1):
        record_chunks.append(DocumentChunk(
            id=f"neml:{raw.pk}:{idx}",
            text=f"{title}\n\n{chunk}",
            source=title,
            source_type="neml",
            record_id=str(clean.source_id),
            status="active",
            is_active=True,
            effective_date="2024",
            metadata={"filename": path.name, "drug_name": title, "category": "NEML"},
        ))
    return text, record_chunks


def build_chunks_from_clean(clean) -> list[DocumentChunk]:
    """Build chunks from an accepted CleanData record (called by ingest_drugs)."""
    path_name = clean.file_name or ""
    title = _title_for(Path(path_name)) if path_name else "Nigeria Essential Medicines List"
    text = clean.raw_text
    chunks = []
    for idx, chunk in enumerate(chunk_text(text), start=1):
        chunks.append(DocumentChunk(
            id=f"neml:{clean.pk}:{idx}",
            text=f"{title}\n\n{chunk}",
            source=title,
            source_type="neml",
            record_id=str(clean.source_id),
            status="active",
            is_active=True,
            effective_date="2024",
            metadata={"filename": path_name, "drug_name": title, "category": "NEML"},
        ))
    return chunks


def _title_for(path: Path) -> str:
    name = path.name.lower()
    if "children" in name or "nemlc" in name:
        return "Nigeria Essential Medicines List for Children, 2nd Edition 2024"
    if "adult" in name:
        return "Nigeria Essential Medicines List for Adults, 8th Edition 2024"
    return f"Nigeria Essential Medicines List - {path.stem}"
