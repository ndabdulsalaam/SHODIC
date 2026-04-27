"""Database storage helpers for ingestion state and processed chunks."""

from __future__ import annotations

from typing import Iterable

from django.db import transaction
from django.utils import timezone

from rxchat.models import DrugChunk, IngestionLog, RawSourceData, ScrapeProgress

from .base import DocumentChunk


def save_raw_record(source: str, source_id: str | int, raw_data: dict, file_name: str = "") -> RawSourceData:
    raw, _ = RawSourceData.objects.update_or_create(
        source=source,
        source_id=str(source_id),
        defaults={
            "raw_data": raw_data,
            "file_name": file_name or "",
        },
    )
    return raw


def get_progress(source: str, default: dict | None = None) -> dict:
    progress, _ = ScrapeProgress.objects.get_or_create(
        source=source,
        defaults={"progress_data": default or {}, "last_run": timezone.now()},
    )
    if default:
        data = dict(progress.progress_data or {})
        changed = False
        for key, value in default.items():
            if key not in data:
                data[key] = value
                changed = True
        if changed:
            progress.progress_data = data
            progress.save(update_fields=["progress_data", "updated_at"])
    return dict(progress.progress_data or {})


def save_progress(source: str, progress_data: dict) -> ScrapeProgress:
    progress, _ = ScrapeProgress.objects.update_or_create(
        source=source,
        defaults={
            "progress_data": progress_data,
            "last_run": timezone.now(),
        },
    )
    return progress


def log_ingestion(source: str, action: str, status: str, **details) -> IngestionLog:
    return IngestionLog.objects.create(
        source=source,
        action=action,
        status=status,
        details=details,
    )


def replace_chunks(raw_source: RawSourceData, chunks: Iterable[DocumentChunk]) -> list[DrugChunk]:
    """Replace processed chunks for one raw source while preserving DB storage."""
    with transaction.atomic():
        existing_point_ids = list(
            raw_source.chunks.exclude(qdrant_point_id__isnull=True)
            .exclude(qdrant_point_id="")
            .values_list("qdrant_point_id", flat=True)
        )
        if existing_point_ids:
            from rxchat.qdrant_service import delete_points  # noqa: PLC0415

            delete_points(existing_point_ids)
        raw_source.chunks.all().delete()
        saved = []
        for index, chunk in enumerate(chunks, start=1):
            saved.append(DrugChunk.objects.create(
                raw_source=raw_source,
                chunk_index=index,
                text=chunk.text,
                metadata={
                    **(chunk.metadata or {}),
                    "source": raw_source.source,
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
        source=metadata.get("source_label") or metadata.get("source") or chunk.raw_source.source,
        source_type=metadata.get("source_type") or chunk.raw_source.source,
        record_id=chunk.raw_source.source_id,
        source_url=metadata.get("source_url", ""),
        status=metadata.get("status", "active"),
        is_active=metadata.get("is_active", True),
        effective_date=metadata.get("effective_date", ""),
        updated_at=chunk.updated_at.isoformat(),
        metadata=metadata,
    )
