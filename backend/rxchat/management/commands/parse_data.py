"""parse_data management command.

Reads RawData uploads, extracts plain text via the appropriate parser,
and writes draft CleanData records.  No chunking or Qdrant interaction.

Run after uploading files via the admin:
    python manage.py parse_data --source neml
    python manage.py parse_data --all
"""

from django.core.management.base import BaseCommand, CommandError

from rxchat.models import CleanData, RawData
from rxchat.ingestion.emdex_parser import parse_emdex
from rxchat.ingestion.neml_parser import parse_neml
from rxchat.ingestion.nhia_stg_parser import parse_nhia_stg
from rxchat.ingestion.nnmda_parser import parse_nnmda
from rxchat.ingestion.who_parser import parse_who_eml


UPLOAD_PARSERS = {
    "neml": parse_neml,
    "nhia_stg": parse_nhia_stg,
    "who": parse_who_eml,
    "nnmda": parse_nnmda,
    "emdex": parse_emdex,
}


class Command(BaseCommand):
    help = (
        "Extract plain text from RawData uploads into CleanData records (status=draft). "
        "Only handles file-uploaded sources (neml, nhia_stg, who, nnmda, emdex). "
        "Scraped sources (nafdac, openfda) write directly to CleanData during scraping. "
        "After parsing, review and Accept records in the admin before running ingest_drugs."
    )

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Parse all upload-based sources.")
        parser.add_argument(
            "--source",
            choices=sorted(UPLOAD_PARSERS),
            help="Parse a single source.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-parse uploads that already have CleanData rows.",
        )

    def handle(self, *args, **options):
        if not options.get("all") and not options.get("source"):
            raise CommandError("Use --all or --source <name>.")

        selected = list(UPLOAD_PARSERS) if options.get("all") else [options["source"]]
        total_records = 0
        total_chunks = 0

        for source in selected:
            parser_fn = UPLOAD_PARSERS[source]
            uploads = RawData.objects.filter(source=source).order_by("uploaded_at")
            if not uploads.exists():
                self.stdout.write(f"{source}: no uploads found — skipping.")
                continue

            source_records = 0
            source_chunks = 0
            skipped_uploads = 0
            for upload in uploads:
                if not options["force"] and CleanData.objects.filter(raw=upload).exists():
                    skipped_uploads += 1
                    continue
                try:
                    extracted, chunks = parser_fn(upload)
                    if isinstance(extracted, list):
                        source_records += len(extracted)
                    else:
                        source_records += 1 if extracted else 0
                    source_chunks += len(chunks)
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(
                        self.style.ERROR(f"{source} upload {upload.pk} ({upload.file.name}): {exc}")
                    )
                    continue

            total_records += source_records
            total_chunks += source_chunks
            self.stdout.write(
                f"{source}: {source_records} record(s), {source_chunks} chunk(s) extracted to CleanData (draft); "
                f"{skipped_uploads} existing upload(s) skipped"
            )

        self.stdout.write(self.style.SUCCESS(
            f"parse_data complete — {total_records} records, {total_chunks} chunks extracted. "
            "Review and Accept them in the admin, then run 'python manage.py ingest_drugs'."
        ))
