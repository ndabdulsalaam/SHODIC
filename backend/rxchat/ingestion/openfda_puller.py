"""OpenFDA drug label puller."""

from __future__ import annotations

import logging
import json
import os
import time
from datetime import timedelta

import requests

from rxchat.models import CleanData

from .base import normalize_name, utc_now
from .nafdac_parser import clean_product, load_raw_products
from .openfda_parser import parse_openfda
from .storage import save_clean_record

logger = logging.getLogger(__name__)


ENDPOINT = "https://api.fda.gov/drug/label.json"
KEY_FIELDS = [
    "openfda.brand_name",
    "openfda.generic_name",
    "openfda.substance_name",
    "openfda.route",
    "indications_and_usage",
    "dosage_and_administration",
    "warnings",
    "adverse_reactions",
    "drug_interactions",
    "contraindications",
    "description",
    "clinical_pharmacology",
]


class OpenFDAPuller:
    """Resumable OpenFDA label API puller."""

    def __init__(
        self,
        endpoint: str = ENDPOINT,
        delay_seconds: float = 0.5,
        session: requests.Session | None = None,
        api_key: str | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.delay_seconds = delay_seconds
        self.session = session or requests.Session()
        self.api_key = api_key if api_key is not None else os.getenv("OPENFDA_API_KEY", "")

    def pull(
        self,
        curated: bool = False,
        resume: bool = False,
        limit: int | None = None,
        recent_days: int | None = None,
    ) -> dict:
        progress = self._load_progress() if resume else self._empty_progress()
        if curated:
            result = self.pull_curated(progress=progress, limit=limit, recent_days=recent_days)
        else:
            result = self.pull_batches(progress=progress, limit=limit, recent_days=recent_days)
        parsed = parse_openfda(curated=curated)
        result.update({
            "processed_records": len(parsed[0]),
            "chunks": len(parsed[1]),
        })
        return result

    def pull_batches(
        self,
        progress: dict | None = None,
        limit: int | None = None,
        recent_days: int | None = None,
    ) -> dict:
        progress = progress or self._load_progress()
        search = self._recent_search(recent_days) if recent_days else None
        pulled = 0
        skip = int(progress.get("next_skip", 0))
        total = None

        while True:
            if limit is not None and pulled >= limit:
                break
            batch_limit = min(100, limit - pulled if limit is not None else 100)
            data = self._request(limit=batch_limit, skip=skip, search=search)
            results = data.get("results", [])
            if total is None:
                total = data.get("meta", {}).get("results", {}).get("total")
            if not results:
                break
            self._save_results(data.get("results", []), batch_key=f"batch:{skip}")
            pulled += len(results)
            skip += len(results)
            progress["next_skip"] = skip
            progress["last_total"] = total
            self._save_progress(progress)
            if len(results) < batch_limit or (total is not None and skip >= int(total)):
                break
            if skip >= 26000 and not search:
                # OpenFDA skip paging is capped. Continue in yearly partitions.
                pulled += self._pull_partitioned(progress, remaining=None if limit is None else limit - pulled)
                break

        return {"mode": "full", "pulled_records": pulled, "total": total}

    def pull_curated(
        self,
        progress: dict | None = None,
        limit: int | None = None,
        recent_days: int | None = None,
    ) -> dict:
        progress = progress or self._load_progress()
        terms = self._nafdac_terms()
        completed = set(progress.get("completed_terms", []))
        pulled = 0
        for term in terms:
            if term in completed:
                continue
            if limit is not None and pulled >= limit:
                break
            search = self._term_search(term)
            if recent_days:
                search = f"({search})+AND+{self._recent_search(recent_days)}"
            batch_limit = min(100, limit - pulled if limit is not None else 100)
            try:
                data = self._request(limit=batch_limit, skip=0, search=search)
            except RuntimeError as exc:
                logger.info("OpenFDA curated term skipped (%s): %s", term, exc)
                completed.add(term)
                progress["completed_terms"] = sorted(completed)
                self._save_progress(progress)
                continue
            self._save_results(data.get("results", []), batch_key=f"curated:{term}")
            pulled += len(data.get("results", []))
            completed.add(term)
            progress["completed_terms"] = sorted(completed)
            self._save_progress(progress)
        return {"mode": "curated", "terms": len(terms), "pulled_records": pulled}

    def _pull_partitioned(self, progress: dict, remaining: int | None = None) -> int:
        pulled = 0
        current_year = utc_now().year
        for year in range(2004, current_year + 1):
            if remaining is not None and pulled >= remaining:
                break
            key = str(year)
            if key in progress.get("completed_years", []):
                continue
            search = f"effective_time:[{year}0101+TO+{year}1231]"
            skip = 0
            while True:
                batch_limit = min(100, remaining - pulled if remaining is not None else 100)
                data = self._request(limit=batch_limit, skip=skip, search=search)
                results = data.get("results", [])
                if not results:
                    break
                self._save_results(data.get("results", []), batch_key=f"batch:{year}:{skip}")
                pulled += len(results)
                skip += len(results)
                if len(results) < batch_limit or skip >= 26000:
                    break
            completed_years = set(progress.get("completed_years", []))
            completed_years.add(key)
            progress["completed_years"] = sorted(completed_years)
            self._save_progress(progress)
        return pulled

    def _request(self, limit: int = 100, skip: int = 0, search: str | None = None) -> dict:
        params = {"limit": limit, "skip": skip}
        if search:
            params["search"] = search
        if self.api_key:
            params["api_key"] = self.api_key
        backoff = 1.0
        last_error: Exception | None = None
        for attempt in range(5):
            if attempt:
                time.sleep(backoff)
                backoff *= 2
            else:
                time.sleep(self.delay_seconds)
            try:
                response = self.session.get(self.endpoint, params=params, timeout=30)
                if response.status_code in {429, 500, 502, 503, 504}:
                    last_error = requests.HTTPError(f"{response.status_code} from OpenFDA")
                    continue
                if response.status_code == 404:
                    return {"meta": {"results": {"total": 0, "skip": skip, "limit": limit}}, "results": []}
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("OpenFDA request failed (%s): %s", attempt + 1, exc)
        raise RuntimeError(f"OpenFDA request failed: {last_error}")

    def _recent_search(self, recent_days: int | None) -> str:
        days = recent_days or 7
        end = utc_now().date()
        start = end - timedelta(days=days)
        return f"effective_time:[{start:%Y%m%d}+TO+{end:%Y%m%d}]"

    def _nafdac_terms(self) -> list[str]:
        terms: set[str] = set()
        for product in (clean_product(item) for item in load_raw_products()):
            for value in [product.get("product_name"), product.get("nrn")]:
                norm = normalize_name(value)
                if norm and len(norm) >= 4:
                    terms.add(norm)
            for ingredient in product.get("active_ingredients") or []:
                norm = normalize_name(ingredient.get("name"))
                if norm and len(norm) >= 4:
                    terms.add(norm)
        return sorted(terms)

    def _term_search(self, term: str) -> str:
        quoted = f'"{term.replace(chr(34), "")}"'
        return (
            f"openfda.brand_name:{quoted}+OR+"
            f"openfda.generic_name:{quoted}+OR+"
            f"openfda.substance_name:{quoted}"
        )

    def _empty_progress(self) -> dict:
        return {"next_skip": 0, "completed_terms": [], "completed_years": []}

    def _load_progress(self) -> dict:
        # No DB model — always start fresh.
        progress = self._empty_progress()
        progress.setdefault("next_skip", 0)
        progress.setdefault("completed_terms", [])
        progress.setdefault("completed_years", [])
        return progress

    def _save_progress(self, progress: dict) -> None:
        # No-op: progress no longer persisted to DB.
        pass

    def _save_results(self, results: list[dict], batch_key: str = "") -> None:
        for idx, label in enumerate(results):
            label_id = label.get("id") or label.get("set_id") or f"{batch_key}:{idx}"
            save_clean_record(
                "openfda",
                str(label_id),
                raw_text=json.dumps({**label, "record_type": "label", "batch_key": batch_key}, ensure_ascii=False),
                data={**label, "record_type": "label", "batch_key": batch_key},
                status=CleanData.STATUS_ACCEPTED,
            )
