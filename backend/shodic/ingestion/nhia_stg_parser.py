"""Parser for NHIA Standard Treatment Guidelines."""

from __future__ import annotations

from pathlib import Path

from shodic.models import SourceFileUpload

from .base import DocumentChunk, chunk_text, extract_text, utc_timestamp
from .storage import replace_chunks, save_raw_record


def parse_nhia_stg() -> tuple[list[dict], list[DocumentChunk]]:
    documents = []
    chunks: list[DocumentChunk] = []

    for upload in SourceFileUpload.objects.filter(source="nhia_stg").order_by("uploaded_at"):
        path = Path(upload.file.path)
        text = extract_text(path)
        if not text.strip():
            continue
        title = "Nigeria Standard Treatment Guidelines"
        document = {
            "filename": path.name,
            "title": title,
            "text": text,
            "parsed_at": utc_timestamp(),
        }
        documents.append(document)
        raw_source = save_raw_record("nhia_stg", f"upload:{upload.pk}", document, file_name=upload.file.name)
        record_chunks = []
        for idx, chunk in enumerate(chunk_text(text), start=1):
            record_chunks.append(DocumentChunk(
                id=f"nhia_stg:{upload.pk}:{idx}",
                text=f"{title}\n\n{chunk}",
                source=title,
                source_type="nhia_stg",
                record_id=str(raw_source.source_id),
                status="active",
                is_active=True,
                metadata={"filename": path.name, "drug_name": title, "category": "NHIA STG"},
            ))
        replace_chunks(raw_source, record_chunks)
        chunks.extend(record_chunks)
    return documents, chunks
