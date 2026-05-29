"""Parser for NNMDA and Nigerian medicinal plant source documents."""

from __future__ import annotations

import re

from pathlib import Path

from shodic.models import SourceFileUpload

from .base import DocumentChunk, chunk_text, extract_text, utc_timestamp
from .storage import replace_chunks, save_raw_record


SCIENTIFIC_NAME_RE = re.compile(r"\b([A-Z][a-z]+ [a-z][a-z\-]+)\b")


def parse_nnmda() -> tuple[list[dict], list[DocumentChunk]]:
    documents = []
    plants = []
    chunks: list[DocumentChunk] = []

    for upload in SourceFileUpload.objects.filter(source="nnmda").order_by("uploaded_at"):
        path = Path(upload.file.path)
        text = extract_text(path)
        if not text.strip():
            continue
        doc = {
            "filename": path.name,
            "title": path.stem.replace("_", " ").title(),
            "text": text,
            "parsed_at": utc_timestamp(),
        }
        documents.append(doc)
        doc_plants = _extract_plants(text, path.name)
        plants.extend(doc_plants)
        raw_source = save_raw_record(
            "nnmda",
            f"upload:{upload.pk}",
            {**doc, "medicinal_plants": doc_plants},
            file_name=upload.file.name,
        )
        record_chunks = []
        for idx, chunk in enumerate(chunk_text(text), start=1):
            record_chunks.append(DocumentChunk(
                id=f"nnmda:{upload.pk}:{idx}",
                text=f"{doc['title']}\n\n{chunk}",
                source="NNMDA Traditional Medicine Sources",
                source_type="nnmda",
                record_id=str(raw_source.source_id),
                status="active",
                is_active=True,
                metadata={"filename": path.name, "drug_name": doc["title"], "category": "NNMDA"},
            ))
        replace_chunks(raw_source, record_chunks)
        chunks.extend(record_chunks)
    return documents, chunks


def _extract_plants(text: str, filename: str) -> list[dict]:
    plants = []
    seen: set[str] = set()
    for match in SCIENTIFIC_NAME_RE.finditer(text):
        scientific_name = match.group(1)
        if scientific_name in seen:
            continue
        seen.add(scientific_name)
        start = max(0, match.start() - 160)
        end = min(len(text), match.end() + 300)
        context = re.sub(r"\s+", " ", text[start:end]).strip()
        plants.append({
            "scientific_name": scientific_name,
            "local_names": [],
            "traditional_uses": context,
            "parts_used": "",
            "preparation_methods": "",
            "safety_notes": "",
            "source_file": filename,
        })
    return plants
