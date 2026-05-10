"""Database storage helpers for ingestion state and processed chunks."""

from __future__ import annotations

from typing import Iterable

from django.db import transaction
from django.utils import timezone

from rxchat.models import CleanData, DrugChunk

from .base import DocumentChunk


def save_clean_record(
    source: str,
    source_id: str | int,
    raw_text: str,
    file_name: str = "",
    raw_id: int | None = None,
    data: dict | None = None,
    status: str = CleanData.STATUS_DRAFT,
) -> CleanData:
    """Upsert a CleanData row with extracted text and optional structured JSON.

    Called by ``parse_data`` after extracting text from a RawData file or a
    scraper response.  Upload records stay in draft until an admin accepts
    them; automated sources can pass structured data and an accepted status.
    """
    clean, _ = CleanData.objects.update_or_create(
        source=source,
        source_id=str(source_id),
        defaults={
            "raw_text": raw_text,
            "data": data or {},
            "file_name": file_name or "",
            "raw_id": raw_id,
            "status": status,
        },
    )
    return clean


def replace_chunks(clean_data: CleanData, chunks: Iterable[DocumentChunk]) -> list[DrugChunk]:
    """Replace processed chunks for one CleanData record."""
    with transaction.atomic():
        existing_point_ids = list(
            clean_data.chunks.exclude(qdrant_point_id__isnull=True)
            .exclude(qdrant_point_id="")
            .values_list("qdrant_point_id", flat=True)
        )
        if existing_point_ids:
            from rxchat.qdrant_service import delete_points  # noqa: PLC0415
            delete_points(existing_point_ids)
        clean_data.chunks.all().delete()
        saved = []
        for index, chunk in enumerate(chunks, start=1):
            saved.append(DrugChunk.objects.create(
                clean_data=clean_data,
                chunk_index=index,
                text=chunk.text,
                metadata={
                    **(chunk.metadata or {}),
                    "source": clean_data.source,
                    "category": (chunk.metadata or {}).get("category", ""),
                    "source_type": chunk.source_type,
                    "source_url": chunk.source_url,
                    "status": chunk.status,
                    "is_active": chunk.is_active,
                    "effective_date": chunk.effective_date,
                    "source_label": chunk.source,
                },
            ))
    return saved


def document_chunk_from_db(chunk: DrugChunk) -> DocumentChunk:
    metadata = dict(chunk.metadata or {})
    return DocumentChunk(
        id=f"drugchunk:{chunk.pk}",
        text=chunk.text,
        source=metadata.get("source_label") or metadata.get("source") or chunk.clean_data.source,
        source_type=metadata.get("source_type") or chunk.clean_data.source,
        record_id=chunk.clean_data.source_id,
        source_url=metadata.get("source_url", ""),
        status=metadata.get("status", "active"),
        is_active=metadata.get("is_active", True),
        effective_date=metadata.get("effective_date", ""),
        updated_at=chunk.updated_at.isoformat(),
        metadata=metadata,
    )
