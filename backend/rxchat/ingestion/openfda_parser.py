"""OpenFDA label parser and chunk builder."""

from __future__ import annotations

from typing import Any

from rxchat.models import RawSourceData

from .base import DocumentChunk, chunk_text, normalize_name, utc_timestamp
from .nafdac_parser import clean_product, load_raw_products
from .storage import replace_chunks


LABEL_FIELDS = [
    "indications_and_usage",
    "dosage_and_administration",
    "warnings",
    "boxed_warning",
    "adverse_reactions",
    "drug_interactions",
    "contraindications",
    "description",
    "clinical_pharmacology",
]


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip() if value else ""


def _names_from_openfda(openfda: dict) -> list[str]:
    names = []
    for field in ["brand_name", "generic_name", "substance_name"]:
        value = openfda.get(field) or []
        if isinstance(value, list):
            names.extend(value)
        elif value:
            names.append(value)
    return [name for name in names if name]


def load_raw_labels() -> list[dict]:
    labels = []
    seen: set[str] = set()
    for row in RawSourceData.objects.filter(source="openfda").order_by("source_id"):
        label = row.raw_data or {}
        if label.get("record_type") not in {"label", None}:
            continue
        label_id = label.get("id") or label.get("set_id") or row.source_id
        if label_id and label_id in seen:
            continue
        if label_id:
            seen.add(label_id)
        labels.append({**label, "_raw_source_id": row.id})
    return labels


def nafdac_match_terms() -> set[str]:
    terms: set[str] = set()
    for product in (clean_product(item) for item in load_raw_products()):
        for value in [product.get("product_name")]:
            norm = normalize_name(value)
            if norm:
                terms.add(norm)
        for ingredient in product.get("active_ingredients") or []:
            norm = normalize_name(ingredient.get("name"))
            if norm:
                terms.add(norm)
    return terms


def _matches_nafdac(label: dict, terms: set[str]) -> bool:
    names = _names_from_openfda(label.get("openfda") or {})
    normalized = [normalize_name(name) for name in names]
    for term in terms:
        if any(term in name or name in term for name in normalized if name):
            return True
    return False


def clean_label(label: dict) -> dict:
    openfda = label.get("openfda") or {}
    sections = {field: _as_text(label.get(field)) for field in LABEL_FIELDS if _as_text(label.get(field))}
    return {
        "id": label.get("id") or label.get("set_id") or "",
        "set_id": label.get("set_id") or "",
        "effective_time": label.get("effective_time") or "",
        "version": label.get("version") or "",
        "brand_name": openfda.get("brand_name") or [],
        "generic_name": openfda.get("generic_name") or [],
        "substance_name": openfda.get("substance_name") or [],
        "route": openfda.get("route") or [],
        "manufacturer_name": openfda.get("manufacturer_name") or [],
        "product_type": openfda.get("product_type") or [],
        "sections": sections,
        "source_url": "https://api.fda.gov/drug/label.json",
        "parsed_at": utc_timestamp(),
        "_raw_source_id": label.get("_raw_source_id"),
    }


def label_to_text(label: dict) -> str:
    names = label.get("brand_name") or label.get("generic_name") or label.get("substance_name") or []
    title = ", ".join(names[:4]) if names else label.get("id")
    lines = [
        f"OpenFDA drug label: {title}",
        f"Generic names: {', '.join(label.get('generic_name') or [])}",
        f"Substances: {', '.join(label.get('substance_name') or [])}",
        f"Route: {', '.join(label.get('route') or [])}",
        f"Manufacturer: {', '.join(label.get('manufacturer_name') or [])}",
        f"Effective time: {label.get('effective_time')}",
        f"Version: {label.get('version')}",
    ]
    for field, text in (label.get("sections") or {}).items():
        label_name = field.replace("_", " ").title()
        lines.append(f"{label_name}: {text}")
    return "\n".join(line for line in lines if line and not line.endswith(": "))


def labels_to_chunks(labels: list[dict]) -> list[DocumentChunk]:
    chunks = []
    for label in labels:
        text = label_to_text(label)
        for idx, chunk in enumerate(chunk_text(text), start=1):
            label_id = label.get("id") or label.get("set_id") or "unknown"
            chunks.append(DocumentChunk(
                id=f"openfda:{label_id}:{idx}",
                text=chunk,
                source="OpenFDA Drug Label",
                source_type="openfda_label",
                record_id=label_id,
                source_url=label.get("source_url") or "https://api.fda.gov/drug/label.json",
                status="active",
                is_active=True,
                effective_date=label.get("effective_time") or "",
                updated_at=label.get("parsed_at") or utc_timestamp(),
                metadata={
                    "drug_name": ", ".join(label.get("brand_name") or label.get("generic_name") or []),
                    "category": "OpenFDA drug label",
                    "set_id": label.get("set_id"),
                    "version": label.get("version"),
                    "brand_name": label.get("brand_name"),
                    "generic_name": label.get("generic_name"),
                    "substance_name": label.get("substance_name"),
                },
            ))
    return chunks


def parse_openfda(curated: bool = False) -> tuple[list[dict], list[DocumentChunk]]:
    labels = [clean_label(label) for label in load_raw_labels()]
    if curated:
        terms = nafdac_match_terms()
        if terms:
            labels = [label for label in labels if _matches_nafdac({
                "openfda": {
                    "brand_name": label.get("brand_name"),
                    "generic_name": label.get("generic_name"),
                    "substance_name": label.get("substance_name"),
                }
            }, terms)]
    chunks = labels_to_chunks(labels)
    chunks_by_record: dict[str, list[DocumentChunk]] = {}
    for chunk in chunks:
        chunks_by_record.setdefault(chunk.record_id, []).append(chunk)
    raw_by_source_id = {
        row.source_id: row
        for row in RawSourceData.objects.filter(source="openfda", source_id__in=chunks_by_record)
    }
    for source_id, record_chunks in chunks_by_record.items():
        raw_source = raw_by_source_id.get(source_id)
        if raw_source:
            replace_chunks(raw_source, record_chunks)
    return labels, chunks
