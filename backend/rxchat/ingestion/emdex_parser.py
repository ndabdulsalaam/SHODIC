"""Parser for licensed EMDEX source uploads."""

from __future__ import annotations

from pathlib import Path

from rxchat.models import SourceFileUpload

from .base import DocumentChunk, chunk_text, extract_text, utc_timestamp
from .storage import replace_chunks, save_raw_record


def parse_emdex() -> tuple[list[dict], list[DocumentChunk]]:
    documents = []
    chunks: list[DocumentChunk] = []

    for upload in SourceFileUpload.objects.filter(source="emdex").order_by("uploaded_at"):
        path = Path(upload.file.path)
        text = extract_text(path)
        if not text.strip():
            continue
        title = f"EMDEX - {path.stem}"
        document = {
            "filename": path.name,
            "title": title,
            "text": text,
            "parsed_at": utc_timestamp(),
            "license_note": "Licensed EMDEX upload",
        }
        documents.append(document)
        raw_source = save_raw_record("emdex", f"upload:{upload.pk}", document, file_name=upload.file.name)
        record_chunks = []
        for idx, chunk in enumerate(chunk_text(text), start=1):
            record_chunks.append(DocumentChunk(
                id=f"emdex:{upload.pk}:{idx}",
                text=f"{title}\n\n{chunk}",
                source=title,
                source_type="emdex",
                record_id=str(raw_source.source_id),
                status="active",
                is_active=True,
                effective_date="",
                metadata={"filename": path.name, "drug_name": title, "category": "EMDEX"},
            ))
        replace_chunks(raw_source, record_chunks)
        chunks.extend(record_chunks)
    return documents, chunks
