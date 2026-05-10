"""Parser for NNMDA and Nigerian medicinal plant source documents."""

from __future__ import annotations

import re
from pathlib import Path

from .base import DocumentChunk, chunk_text, extract_text
from .storage import save_clean_record


SCIENTIFIC_NAME_RE = re.compile(r"\b([A-Z][a-z]+ [a-z][a-z\-]+)\b")


def parse_nnmda(raw) -> tuple[str, list[DocumentChunk]]:
    """Extract text from a single RawData upload."""
    path = Path(raw.file.path)
    text = extract_text(path)

    clean = save_clean_record(
        "nnmda",
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
    title = Path(path_name).stem.replace("_", " ").title() if path_name else "NNMDA"
    chunks = []
    for idx, chunk in enumerate(chunk_text(text), start=1):
        chunks.append(DocumentChunk(
            id=f"nnmda:{clean.pk}:{idx}",
            text=f"{title}\n\n{chunk}",
            source="NNMDA Traditional Medicine Sources",
            source_type="nnmda",
            record_id=str(clean.source_id),
            status="active",
            is_active=True,
            metadata={"filename": path_name, "drug_name": title, "category": "NNMDA"},
        ))
    return chunks


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
