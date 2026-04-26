"""Parser for NAFDAC Greenbook raw JSON."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from chat.models import RawSourceData

from .base import (
    DocumentChunk,
    chunk_text,
    merge_unique,
    normalize_name,
    utc_timestamp,
)
from .storage import replace_chunks


INACTIVE_STATUSES = {"expired", "inactive", "withdrawn", "suspended", "removed", "cancelled", "canceled"}


def is_active_product(status: str | None) -> bool:
    value = normalize_name(status)
    return bool(value) and not any(flag in value for flag in INACTIVE_STATUSES)


def load_raw_products() -> list[dict]:
    products = []
    for row in RawSourceData.objects.filter(source="nafdac").order_by("source_id"):
        data = row.raw_data or {}
        if data.get("record_type") not in {"product_detail", None}:
            continue
        if isinstance(data, dict) and data.get("product_id"):
            products.append({**data, "_raw_source_id": row.id})
    return products


def clean_product(product: dict) -> dict:
    status = product.get("status") or "Unknown"
    ingredients = product.get("active_ingredients") or []
    cleaned_ingredients = []
    for ingredient in ingredients:
        if isinstance(ingredient, dict):
            name = (ingredient.get("name") or "").strip()
            strength = (ingredient.get("strength") or "").strip()
            if name:
                cleaned_ingredients.append({"name": name, "strength": strength})
    return {
        "product_id": product.get("product_id"),
        "product_name": (product.get("product_name") or "").strip(),
        "dosage_form": (product.get("dosage_form") or "").strip(),
        "route": (product.get("route") or "").strip(),
        "active_ingredients": cleaned_ingredients,
        "nrn": (product.get("nrn") or "").strip(),
        "status": status,
        "is_active": is_active_product(status),
        "category": (product.get("category") or "").strip(),
        "category_id": product.get("category_id"),
        "manufacturer": (product.get("manufacturer") or "").strip(),
        "manufacturer_country": (product.get("manufacturer_country") or "").strip(),
        "applicant": (product.get("applicant") or "").strip(),
        "atc_code": (product.get("atc_code") or "").strip(),
        "marketing_category": (product.get("marketing_category") or "").strip(),
        "registration_date": (product.get("registration_date") or "").strip(),
        "expiry_date": (product.get("expiry_date") or "").strip(),
        "pack_size": (product.get("pack_size") or "").strip(),
        "composition": (product.get("composition") or "").strip(),
        "product_description": (product.get("product_description") or "").strip(),
        "scraped_at": product.get("scraped_at") or utc_timestamp(),
        "source_url": product.get("source_url") or "",
        "_raw_source_id": product.get("_raw_source_id"),
    }


def _active_indexes(products: Iterable[dict]) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    by_ingredient: dict[str, list[dict]] = defaultdict(list)
    by_atc: dict[str, list[dict]] = defaultdict(list)
    for product in products:
        if not product.get("is_active"):
            continue
        for ingredient in product.get("active_ingredients") or []:
            key = normalize_name(ingredient.get("name"))
            if key:
                by_ingredient[key].append(product)
        atc = normalize_name(product.get("atc_code"))
        if atc and atc != "na":
            by_atc[atc].append(product)
    return by_ingredient, by_atc


def _alternative_names(product: dict, by_ingredient: dict[str, list[dict]], by_atc: dict[str, list[dict]]) -> list[str]:
    candidates = []
    for ingredient in product.get("active_ingredients") or []:
        candidates.extend(by_ingredient.get(normalize_name(ingredient.get("name")), []))
    candidates.extend(by_atc.get(normalize_name(product.get("atc_code")), []))
    return merge_unique(
        candidate.get("product_name")
        for candidate in candidates
        if candidate.get("product_id") != product.get("product_id")
    )[:5]


def product_to_text(product: dict, alternatives: list[str] | None = None) -> str:
    ingredients = product.get("active_ingredients") or []
    ingredient_text = "; ".join(
        f"{item.get('name', '')} {item.get('strength', '')}".strip()
        for item in ingredients
        if item.get("name")
    )
    status = product.get("status") or "Unknown"
    lines = [
        f"NAFDAC Greenbook product: {product.get('product_name')}",
        f"Status: {status}",
    ]
    if not product.get("is_active"):
        alt_text = ", ".join(alternatives or [])
        advice = "This product is not currently marked active in the NAFDAC Greenbook."
        if alt_text:
            advice += f" Active alternatives or replacements to verify include: {alt_text}."
        advice += " Confirm current availability and a suitable replacement with a pharmacist or prescriber."
        lines.append(advice)
    lines.extend([
        f"NAFDAC registration number: {product.get('nrn')}",
        f"Category: {product.get('category')}",
        f"Dosage form: {product.get('dosage_form')}",
        f"Route: {product.get('route')}",
        f"Active ingredients: {ingredient_text}",
        f"ATC code: {product.get('atc_code')}",
        f"Marketing category: {product.get('marketing_category')}",
        f"Applicant: {product.get('applicant')}",
        f"Manufacturer: {product.get('manufacturer')} ({product.get('manufacturer_country')})",
        f"Approval date: {product.get('registration_date')}",
        f"Expiry date: {product.get('expiry_date')}",
        f"Pack size: {product.get('pack_size')}",
        f"Composition: {product.get('composition')}",
        f"Description: {product.get('product_description')}",
    ])
    return "\n".join(line for line in lines if line and not line.endswith(": "))


def products_to_chunks(products: list[dict]) -> list[DocumentChunk]:
    by_ingredient, by_atc = _active_indexes(products)
    chunks: list[DocumentChunk] = []
    for product in products:
        alternatives = _alternative_names(product, by_ingredient, by_atc)
        text = product_to_text(product, alternatives)
        for idx, chunk in enumerate(chunk_text(text), start=1):
            product_id = str(product.get("product_id") or "")
            chunks.append(DocumentChunk(
                id=f"nafdac:{product_id}:{idx}",
                text=chunk,
                source=f"NAFDAC Greenbook - {product.get('category') or 'Product'}",
                source_type="nafdac_greenbook",
                record_id=product_id,
                source_url=product.get("source_url") or "",
                status=product.get("status") or "Unknown",
                is_active=bool(product.get("is_active")),
                effective_date=product.get("registration_date") or "",
                updated_at=product.get("scraped_at") or utc_timestamp(),
                metadata={
                    "drug_name": product.get("product_name"),
                    "product_name": product.get("product_name"),
                    "category": product.get("category"),
                    "nrn": product.get("nrn"),
                    "atc_code": product.get("atc_code"),
                    "category_id": product.get("category_id"),
                    "expiry_date": product.get("expiry_date"),
                    "alternatives": alternatives,
                },
            ))
    return chunks


def parse_nafdac() -> tuple[list[dict], list[DocumentChunk]]:
    products = [clean_product(product) for product in load_raw_products()]
    chunks = products_to_chunks(products)
    chunks_by_record: dict[str, list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        chunks_by_record[chunk.record_id].append(chunk)
    raw_by_source_id = {
        row.source_id: row
        for row in RawSourceData.objects.filter(source="nafdac", source_id__in=chunks_by_record)
    }
    for source_id, record_chunks in chunks_by_record.items():
        raw_source = raw_by_source_id.get(source_id)
        if raw_source:
            replace_chunks(raw_source, record_chunks)
    return products, chunks
