"""Periodic update checks for RxChat data sources."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.management import call_command
from django.utils import timezone

from chat.models import SourceFileUpload

from .base import append_ingestion_log, utc_now
from .source_status import source_status_rows


STATIC_SOURCE_POLICIES = {
    "neml": 365,
    "nhia_stg": 365,
    "who": 730,
    "nnmda": 365,
    "emdex": 365,
}


def newest_upload_age_days(source: str) -> int | None:
    upload = SourceFileUpload.objects.filter(source=source).order_by("-uploaded_at").first()
    if not upload:
        return None
    return int((timezone.now() - upload.uploaded_at).total_seconds() // 86400)


def check_static_sources() -> list[dict[str, Any]]:
    results = []
    for source, max_age in STATIC_SOURCE_POLICIES.items():
        age = newest_upload_age_days(source)
        status = "missing" if age is None else "stale" if age > max_age else "fresh"
        result = {
            "source": source,
            "status": status,
            "age_days": age,
            "max_age_days": max_age,
        }
        append_ingestion_log(source, "static_source_age_check", status, **result)
        results.append(result)
    return results


def check_all_sources() -> dict[str, Any]:
    rows = source_status_rows()
    static_results = check_static_sources()
    summary = {
        "manual_status": rows,
        "static_age_checks": static_results,
    }
    append_ingestion_log("all", "source_status_check", "ok", missing=[
        row["source"] for row in rows if row["status"] == "missing"
    ])
    return summary


def run_nafdac_delta() -> None:
    call_command("scrape_nafdac", "--resume", "--delta")


def run_nafdac_full() -> None:
    call_command("scrape_nafdac", "--resume")


def run_openfda_recent(days: int = 7) -> None:
    call_command("pull_openfda", "--curated", "--resume", "--recent-days", str(days))


def schedule_defaults() -> list[dict[str, Any]]:
    next_run = utc_now() + timedelta(minutes=5)
    return [
        {
            "name": "RxChat weekly NAFDAC delta",
            "func": "django.core.management.call_command",
            "args": "'scrape_nafdac', '--resume', '--delta'",
            "schedule_type": "W",
            "next_run": next_run,
        },
        {
            "name": "RxChat monthly NAFDAC full scrape",
            "func": "django.core.management.call_command",
            "args": "'scrape_nafdac', '--resume'",
            "schedule_type": "M",
            "next_run": next_run,
        },
        {
            "name": "RxChat weekly OpenFDA recent pull",
            "func": "django.core.management.call_command",
            "args": "'pull_openfda', '--curated', '--resume', '--recent-days', '7'",
            "schedule_type": "W",
            "next_run": next_run,
        },
        {
            "name": "RxChat annual static source check",
            "func": "chat.ingestion.update_checker.check_all_sources",
            "args": "",
            "schedule_type": "Y",
            "next_run": next_run,
        },
    ]
