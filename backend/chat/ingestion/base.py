"""Shared helpers for RxChat data ingestion."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp() -> str:
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_ingestion_log(source: str, event: str, status: str, **details: Any) -> dict[str, Any]:
    entry = {
        "source": source,
        "event": event,
        "status": status,
        "checked_at": utc_timestamp(),
        "details": details,
    }
    try:
        from .storage import log_ingestion  # noqa: PLC0415

        log_ingestion(source, event, status, **details)
    except Exception:
        pass
    return entry


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9+]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def slugify(value: str | None, fallback: str = "item") -> str:
    slug = normalize_name(value).replace(" ", "_")
    slug = re.sub(r"[^a-z0-9_]+", "", slug)
    return slug[:80] or fallback


def split_multi_value(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"\s*;\s*|\s*,\s*(?=[A-Z][A-Za-z])", value)
    return [part.strip() for part in parts if part.strip()]


def merge_unique(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in values:
        cleaned = (value or "").strip()
        key = normalize_name(cleaned)
        if cleaned and key not in seen:
            seen.add(key)
            merged.append(cleaned)
    return merged


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> list[str]:
    cleaned = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        if end < len(cleaned):
            boundary = cleaned.rfind("\n\n", start, end)
            if boundary <= start + max_chars // 2:
                boundary = cleaned.rfind(". ", start, end)
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


@dataclass(slots=True)
class DocumentChunk:
    id: str
    text: str
    source: str
    source_type: str
    record_id: str = ""
    source_url: str = ""
    status: str = "active"
    is_active: bool = True
    effective_date: str = ""
    updated_at: str = field(default_factory=utc_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "record_id": self.record_id,
            "status": self.status,
            "is_active": self.is_active,
            "effective_date": self.effective_date,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, **self.payload()}

def extract_text(path: Path) -> str:
    """Extract readable text from supported manual source files."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber  # noqa: PLC0415

            pages = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    pages.append(page.extract_text() or "")
            return "\n\n".join(page for page in pages if page.strip())
        except Exception:
            return _markitdown_text(path)
    if suffix in {".xlsx", ".xlsm"}:
        try:
            import openpyxl  # noqa: PLC0415

            workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
            lines = []
            for sheet in workbook.worksheets:
                lines.append(f"Sheet: {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                    if values:
                        lines.append(" | ".join(values))
            return "\n".join(lines)
        except Exception:
            return _markitdown_text(path)
    if suffix in {".csv", ".tsv"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    return _markitdown_text(path)


def _markitdown_text(path: Path) -> str:
    try:
        from markitdown import MarkItDown  # noqa: PLC0415

        result = MarkItDown().convert(str(path))
        return getattr(result, "text_content", "") or ""
    except Exception:
        return ""
