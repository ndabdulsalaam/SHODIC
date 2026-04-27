"""Parser for WHO Essential Medicines List exports."""

from __future__ import annotations

import csv
from pathlib import Path

from rxchat.models import SourceFileUpload

from .base import DocumentChunk, chunk_text, utc_timestamp
from .storage import replace_chunks, save_raw_record


def parse_who_eml() -> tuple[list[dict], list[DocumentChunk]]:
    records = []
    chunks: list[DocumentChunk] = []
    for upload in SourceFileUpload.objects.filter(source="who").order_by("uploaded_at"):
        path = Path(upload.file.path)
        upload_records = _read_records(path)
        for idx, record in enumerate(upload_records, start=1):
            record = {**record, "file_name": path.name, "upload_id": upload.pk}
            raw_source = save_raw_record("who", f"upload:{upload.pk}:row:{idx}", record, file_name=upload.file.name)
            record_chunks = records_to_chunks([record], record_id=str(raw_source.source_id), id_prefix=f"who:{upload.pk}:{idx}")
            replace_chunks(raw_source, record_chunks)
            chunks.extend(record_chunks)
            records.append(record)
    return records, chunks


def _read_records(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [_clean_row(row) for row in csv.DictReader(handle)]

    import openpyxl  # noqa: PLC0415

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    records = []
    for row in rows[1:]:
        data = {
            headers[idx]: value
            for idx, value in enumerate(row)
            if idx < len(headers) and headers[idx]
        }
        if any(value not in {None, ""} for value in data.values()):
            records.append(_clean_row(data))
    return records


def _clean_row(row: dict) -> dict:
    normalized = {str(key).strip().lower().replace(" ", "_"): value for key, value in row.items()}
    return {
        "medicine_name": _pick(normalized, "medicine_name", "medicine", "inn", "name"),
        "category": _pick(normalized, "category", "section", "eml_section"),
        "formulation": _pick(normalized, "formulation", "formulations", "dosage_form"),
        "strength": _pick(normalized, "strength", "strengths"),
        "therapeutic_section": _pick(normalized, "therapeutic_section", "section"),
        "raw": {key: str(value).strip() for key, value in row.items() if value not in {None, ""}},
        "parsed_at": utc_timestamp(),
    }


def _pick(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in {None, ""}:
            return str(value).strip()
    return ""


def records_to_chunks(records: list[dict], record_id: str | None = None, id_prefix: str = "who") -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for idx, record in enumerate(records, start=1):
        title = record.get("medicine_name") or f"WHO EML record {idx}"
        text = "\n".join([
            f"WHO Essential Medicines List medicine: {title}",
            f"Category: {record.get('category')}",
            f"Therapeutic section: {record.get('therapeutic_section')}",
            f"Formulation: {record.get('formulation')}",
            f"Strength: {record.get('strength')}",
        ])
        for chunk_idx, chunk in enumerate(chunk_text(text), start=1):
            chunks.append(DocumentChunk(
                id=f"{id_prefix}:{chunk_idx}",
                text=chunk,
                source="WHO Essential Medicines List",
                source_type="who_eml",
                record_id=record_id or str(idx),
                status="active",
                is_active=True,
                metadata={"medicine_name": title, "drug_name": title, "category": record.get("category") or "WHO EML"},
            ))
    return chunks
