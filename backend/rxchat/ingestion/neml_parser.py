"""Parser for Nigeria Essential Medicines List PDFs."""

from __future__ import annotations

from pathlib import Path

from rxchat.models import SourceFileUpload

from .base import DocumentChunk, chunk_text, extract_text, utc_timestamp
from .storage import replace_chunks, save_raw_record


def parse_neml() -> tuple[list[dict], list[DocumentChunk]]:
    documents = []
    chunks: list[DocumentChunk] = []

    for upload in SourceFileUpload.objects.filter(source="neml").order_by("uploaded_at"):
        path = Path(upload.file.path)
        text = extract_text(path)
        if not text.strip():
            continue
        title = _title_for(path)
        document = {
            "filename": path.name,
            "title": title,
            "text": text,
            "parsed_at": utc_timestamp(),
        }
        documents.append(document)
        raw_source = save_raw_record("neml", f"upload:{upload.pk}", document, file_name=upload.file.name)
        record_chunks = []
        for idx, chunk in enumerate(chunk_text(text), start=1):
            record_chunks.append(DocumentChunk(
                id=f"neml:{upload.pk}:{idx}",
                text=f"{title}\n\n{chunk}",
                source=title,
                source_type="neml",
                record_id=str(raw_source.source_id),
                status="active",
                is_active=True,
                effective_date="2024",
                metadata={"filename": path.name, "drug_name": title, "category": "NEML"},
            ))
        replace_chunks(raw_source, record_chunks)
        chunks.extend(record_chunks)
    return documents, chunks


def _title_for(path: Path) -> str:
    name = path.name.lower()
    if "children" in name or "nemlc" in name:
        return "Nigeria Essential Medicines List for Children, 2nd Edition 2024"
    if "adult" in name:
        return "Nigeria Essential Medicines List for Adults, 8th Edition 2024"
    return f"Nigeria Essential Medicines List - {path.stem}"
