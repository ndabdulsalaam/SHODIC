"""NAFDAC Greenbook scraper."""

from __future__ import annotations

import logging
import json
import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - exercised only before requirements install
    BeautifulSoup = None

from rxchat.models import CleanData

from .base import split_multi_value, utc_timestamp
from .storage import save_clean_record

logger = logging.getLogger(__name__)


BASE_URL = "https://greenbook.nafdac.gov.ng"
DETAIL_RE = re.compile(r"/products/details/(\d+)")
NRN_RE = re.compile(r"\bNRN:\s*([A-Z0-9\-]+)", re.IGNORECASE)

NAFDAC_CATEGORIES = {
    1: "Drugs",
    2: "Vaccines and Biologics",
    5: "Medical devices",
    6: "Veterinary",
    7: "Herbals and Nutraceuticals",
    12: "Disinfectants",
}

DETAIL_LABELS = {
    "roa",
    "applicant name",
    "nrn",
    "status",
    "composition",
    "atc code/atcvet code",
    "product category",
    "marketing category",
    "packsize",
    "product description",
    "manufacturer name",
    "manufacturer country",
    "approval date",
    "expiry date",
}


@dataclass(frozen=True)
class ListingPage:
    records: list[dict]
    next_url: str | None


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _norm_label(value: str | None) -> str:
    return _clean_text(value).lower().strip("#: ")


def _detail_id_from_url(url: str) -> str:
    match = DETAIL_RE.search(url)
    return match.group(1) if match else ""


def parse_listing_html(html: str, category_id: int, url: str) -> ListingPage:
    """Parse a category listing page into product detail links."""
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required to parse NAFDAC Greenbook pages.")
    soup = BeautifulSoup(html, "lxml")
    records: list[dict] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = DETAIL_RE.search(href)
        if not match:
            continue
        product_id = match.group(1)
        if product_id in seen:
            continue
        seen.add(product_id)
        listing_text = _clean_text(link.get_text(" ", strip=True))
        nrn_match = NRN_RE.search(listing_text)
        name_guess = NRN_RE.sub("", listing_text)
        name_guess = re.split(r"\s*(?:##|\*\*|__|_#|#)\s*", name_guess)[0]
        records.append({
            "product_id": int(product_id),
            "product_name": _clean_text(name_guess),
            "nrn": nrn_match.group(1) if nrn_match else "",
            "category": NAFDAC_CATEGORIES.get(category_id, str(category_id)),
            "category_id": category_id,
            "listing_text": listing_text,
            "detail_url": urljoin(BASE_URL, href),
            "source_url": url,
        })

    next_url = None
    for link in soup.find_all("a", href=True):
        text = _clean_text(link.get_text(" ", strip=True)).lower()
        rel = " ".join(link.get("rel") or []).lower()
        if text in {"next", "next >", ">", ">>"} or "next" in rel:
            next_url = urljoin(url, link["href"])
            break

    return ListingPage(records=records, next_url=next_url)


def _value_after(texts: list[str], label: str) -> str:
    label_norm = _norm_label(label)
    for idx, text in enumerate(texts):
        if _norm_label(text) != label_norm:
            continue
        if idx + 1 >= len(texts):
            return ""
        value = texts[idx + 1]
        if _norm_label(value) in DETAIL_LABELS:
            return ""
        return value
    return ""


def _intro_values(texts: list[str]) -> tuple[str, str, str, str]:
    try:
        idx = next(i for i, text in enumerate(texts) if _norm_label(text) == "product details")
    except StopIteration:
        idx = -1

    values = []
    for text in texts[idx + 1:]:
        if _norm_label(text) in DETAIL_LABELS:
            break
        values.append(text)

    product_name = values[0] if values else ""
    ingredients = values[1] if len(values) > 1 else ""
    strengths = values[2] if len(values) > 2 else ""
    dosage_form = values[3] if len(values) > 3 else ""
    return product_name, ingredients, strengths, dosage_form


def _ingredient_list(names: str, strengths: str) -> list[dict[str, str]]:
    name_parts = split_multi_value(names)
    strength_parts = split_multi_value(strengths)
    if not name_parts and names:
        name_parts = [names]
    ingredients = []
    for idx, name in enumerate(name_parts):
        strength = strength_parts[idx] if idx < len(strength_parts) else ""
        ingredients.append({"name": name, "strength": strength})
    return ingredients


def parse_detail_html(html: str, product_id: int | str, source_url: str) -> dict:
    """Parse a NAFDAC product detail page into normalized JSON."""
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required to parse NAFDAC Greenbook pages.")
    soup = BeautifulSoup(html, "lxml")
    texts = [_clean_text(text) for text in soup.stripped_strings if _clean_text(text)]
    product_name, ingredients_text, strengths_text, dosage_form = _intro_values(texts)
    status = _value_after(texts, "Status") or "Unknown"

    return {
        "product_id": int(product_id),
        "product_name": product_name,
        "dosage_form": dosage_form,
        "route": _value_after(texts, "ROA"),
        "active_ingredients": _ingredient_list(ingredients_text, strengths_text),
        "nrn": _value_after(texts, "NRN"),
        "status": status,
        "category": _value_after(texts, "Product Category"),
        "category_id": _category_id(_value_after(texts, "Product Category")),
        "manufacturer": _value_after(texts, "Manufacturer Name"),
        "manufacturer_country": _value_after(texts, "Manufacturer Country"),
        "applicant": _value_after(texts, "Applicant Name"),
        "atc_code": _value_after(texts, "ATC Code/ATCvet Code"),
        "marketing_category": _value_after(texts, "Marketing Category"),
        "registration_date": _value_after(texts, "Approval Date"),
        "expiry_date": _value_after(texts, "Expiry Date"),
        "pack_size": _value_after(texts, "Packsize"),
        "composition": _value_after(texts, "Composition"),
        "product_description": _value_after(texts, "Product Description"),
        "scraped_at": utc_timestamp(),
        "source_url": source_url,
    }


def _category_id(category_name: str) -> int | None:
    norm = _norm_label(category_name)
    for category_id, label in NAFDAC_CATEGORIES.items():
        if _norm_label(label) == norm:
            return category_id
    return None


class NAFDACGreenbookScraper:
    """Polite, resumable scraper for the NAFDAC Greenbook portal."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        delay_seconds: float = 2.5,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.delay_seconds = delay_seconds
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "RxChat-DataBot/1.0"})

    def run(
        self,
        category: int | None = None,
        resume: bool = False,
        details_only: bool = False,
        delta: bool = False,
        limit: int | None = None,
    ) -> dict:
        progress = self._load_progress() if resume else self._empty_progress()
        categories = [category] if category else list(NAFDAC_CATEGORIES)
        all_listings: list[dict] = []
        detail_count = 0

        for category_id in categories:
            if category_id not in NAFDAC_CATEGORIES:
                raise ValueError(f"Unsupported NAFDAC category: {category_id}")
            if details_only:
                listings = self._stored_listings(category_id)
            else:
                listings = self.scrape_category_listings(category_id, progress, max_pages=2 if delta else None)
            all_listings.extend(listings or [])
            remaining = None if limit is None else max(limit - detail_count, 0)
            if remaining == 0:
                break
            details = self.scrape_details(all_listings if details_only else listings, progress, limit=remaining)
            detail_count += len(details)
            if not delta and category_id not in progress["completed_categories"]:
                progress["completed_categories"].append(category_id)
            self._save_progress(progress)

        return {
            "categories": categories,
            "listing_count": len(all_listings),
            "detail_count": len(progress["scraped_product_ids"]),
            "storage": "database",
        }

    def scrape_category_listings(
        self,
        category_id: int,
        progress: dict | None = None,
        max_pages: int | None = None,
    ) -> list[dict]:
        progress = progress if progress is not None else self._load_progress()
        url = f"{self.base_url}/productCategory/products/{category_id}"
        page = 1
        listings: list[dict] = []
        seen: set[int] = set()

        while url:
            html = self._get(url)
            parsed = parse_listing_html(html, category_id, url)
            for record in parsed.records:
                product_id = int(record["product_id"])
                if product_id not in seen:
                    seen.add(product_id)
                    listings.append(record)
            progress["last_page"][str(category_id)] = page
            self._save_progress(progress)
            if max_pages and page >= max_pages:
                break
            if not parsed.next_url or parsed.next_url == url:
                break
            url = parsed.next_url
            page += 1

        for record in listings:
            save_clean_record(
                "nafdac",
                f"listing:{category_id}:{record['product_id']}",
                raw_text=json.dumps({**record, "record_type": "listing"}, ensure_ascii=False),
                data={**record, "record_type": "listing"},
                status=CleanData.STATUS_ACCEPTED,
            )
        return listings

    def scrape_details(
        self,
        listings: Iterable[dict],
        progress: dict | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        progress = progress if progress is not None else self._load_progress()
        scraped_ids = {str(item) for item in progress.get("scraped_product_ids", [])}
        details: list[dict] = []

        for listing in listings:
            if limit is not None and len(details) >= limit:
                break
            product_id = str(listing.get("product_id") or _detail_id_from_url(listing.get("detail_url", "")))
            if not product_id:
                continue
            existing = CleanData.objects.filter(
                source="nafdac",
                source_id=product_id,
                data__record_type="product_detail",
            ).first()
            if existing:
                if product_id not in scraped_ids:
                    scraped_ids.add(product_id)
                details.append(existing.data)
                continue
            detail_url = listing.get("detail_url") or f"{self.base_url}/products/details/{product_id}"
            html = self._get(detail_url)
            detail = parse_detail_html(html, product_id, detail_url)
            if not detail.get("category"):
                detail["category"] = listing.get("category", "")
                detail["category_id"] = listing.get("category_id")
            detail["record_type"] = "product_detail"
            save_clean_record(
                "nafdac",
                product_id,
                raw_text=json.dumps(detail, ensure_ascii=False),
                data=detail,
                status=CleanData.STATUS_ACCEPTED,
            )
            details.append(detail)
            scraped_ids.add(product_id)
            progress["scraped_product_ids"] = sorted(scraped_ids, key=lambda value: int(value) if value.isdigit() else value)
            self._save_progress(progress)

        progress["scraped_product_ids"] = sorted(scraped_ids, key=lambda value: int(value) if value.isdigit() else value)
        self._save_progress(progress)
        return details

    def _get(self, url: str) -> str:
        backoff = 2.0
        last_error: Exception | None = None
        for attempt in range(5):
            if attempt:
                time.sleep(backoff)
                backoff *= 2
            else:
                time.sleep(self.delay_seconds)
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code in {429, 500, 502, 503, 504}:
                    last_error = requests.HTTPError(f"{response.status_code} from {url}")
                    continue
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("NAFDAC request failed (%s): %s", attempt + 1, exc)
        raise RuntimeError(f"Failed to fetch {url}: {last_error}")

    def _empty_progress(self) -> dict:
        return {"completed_categories": [], "last_page": {}, "scraped_product_ids": []}

    def _load_progress(self) -> dict:
        # Progress is stored in-memory only (no DB model).
        progress = self._empty_progress()
        progress.setdefault("completed_categories", [])
        progress.setdefault("last_page", {})
        progress.setdefault("scraped_product_ids", [])
        return progress

    def _save_progress(self, progress: dict) -> None:
        # No-op: progress no longer persisted to DB.
        pass

    def _stored_listings(self, category_id: int) -> list[dict]:
        prefix = f"listing:{category_id}:"
        return [
            item.data
            for item in CleanData.objects.filter(source="nafdac", source_id__startswith=prefix)
            .order_by("source_id")
        ]
