"""Status table for manual and automated data sources."""

from __future__ import annotations

from dataclasses import dataclass

from chat.models import RawSourceData, SourceFileUpload


@dataclass(frozen=True)
class SourceExpectation:
    source: str
    label: str
    kind: str
    expected_file: str
    save_to: str
    url: str
    command: str = ""


EXPECTATIONS = [
    SourceExpectation(
        source="neml",
        label="NEML Adults",
        kind="Manual PDF",
        expected_file="neml_adults_8th_2024.pdf",
        save_to="neml/raw/",
        url="https://www.health.gov.ng/wp-content/uploads/2025/08/Final-NEML-Adult-8th-Edition.pdf",
    ),
    SourceExpectation(
        source="neml",
        label="NEML Children",
        kind="Manual PDF",
        expected_file="neml_children_2nd_2024.pdf",
        save_to="neml/raw/",
        url="https://www.health.gov.ng/wp-content/uploads/2025/08/Final-NEMLc-2nd-Edition.pdf",
    ),
    SourceExpectation(
        source="nhia_stg",
        label="NHIA STG",
        kind="Manual PDF",
        expected_file="nhia_stg.pdf",
        save_to="nhia_stg/raw/",
        url="https://health.gov.ng/hospital-services-policy/",
    ),
    SourceExpectation(
        source="who",
        label="WHO EML",
        kind="Web export",
        expected_file="who_eml.xlsx",
        save_to="who/raw/",
        url="https://list.essentialmeds.org/",
    ),
    SourceExpectation(
        source="nnmda",
        label="NNMDA",
        kind="Manual PDF/docs",
        expected_file="Medicinal plants inventory",
        save_to="nnmda/raw/",
        url="https://nnmda.gov.ng/",
    ),
    SourceExpectation(
        source="nafdac",
        label="NAFDAC",
        kind="Auto scraper",
        expected_file="-",
        save_to="nafdac/raw/",
        url="",
        command="python manage.py scrape_nafdac --resume",
    ),
    SourceExpectation(
        source="openfda",
        label="OpenFDA",
        kind="Auto API pull",
        expected_file="-",
        save_to="openfda/raw/",
        url="",
        command="python manage.py pull_openfda --curated --resume",
    ),
    SourceExpectation(
        source="emdex",
        label="EMDEX",
        kind="Licensed upload",
        expected_file="EMDEX licensed PDF/Excel",
        save_to="Neon Postgres",
        url="Contact Editor@Emdex.org when licensed, then upload in admin",
    ),
]


def _exists(expectation: SourceExpectation) -> bool:
    if expectation.command:
        return RawSourceData.objects.filter(source=expectation.source).exists()
    return SourceFileUpload.objects.filter(source=expectation.source).exists()


def source_status_rows() -> list[dict[str, str | bool]]:
    rows = []
    for expectation in EXPECTATIONS:
        exists = _exists(expectation)
        upload_count = SourceFileUpload.objects.filter(source=expectation.source).count()
        raw_count = RawSourceData.objects.filter(source=expectation.source).count()
        rows.append({
            "source": expectation.label,
            "type": expectation.kind,
            "expected_file": expectation.expected_file,
            "save_to": "Neon Postgres",
            "present": exists,
            "status": "present" if exists else "missing",
            "url": expectation.url,
            "command": expectation.command,
            "uploads": upload_count,
            "raw_records": raw_count,
        })
    return rows


def format_status_table(rows: list[dict[str, str | bool]] | None = None) -> str:
    rows = rows or source_status_rows()
    headers = ["Source", "Type", "Expected File", "Status", "Action"]
    body = []
    for row in rows:
        action = row.get("command") or row.get("url") or ""
        body.append([
            str(row["source"]),
            str(row["type"]),
            str(row["expected_file"]),
            str(row["status"]),
            str(action),
        ])

    widths = [
        max(len(headers[i]), *(len(item[i]) for item in body)) if body else len(headers[i])
        for i in range(len(headers))
    ]
    lines = [
        " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))),
        "-+-".join("-" * width for width in widths),
    ]
    for item in body:
        lines.append(" | ".join(item[i].ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(lines)


def missing_manual_sources() -> list[dict[str, str | bool]]:
    return [
        row for row in source_status_rows()
        if row["status"] == "missing" and not row.get("command")
    ]
