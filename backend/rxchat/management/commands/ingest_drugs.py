"""ingest_drugs management command.

Reads accepted CleanData records and creates DrugChunk rows.
Does NOT touch Qdrant — run seed_qdrant afterwards to sync.

Usage:
    python manage.py ingest_drugs --all
    python manage.py ingest_drugs --source nafdac
"""
from django.core.management.base import BaseCommand, CommandError

from rxchat.models import CleanData, DrugChunk
from rxchat.ingestion.storage import replace_chunks

from rxchat.ingestion.emdex_parser import build_chunks_from_clean as emdex_chunks
from rxchat.ingestion.nafdac_parser import parse_nafdac
from rxchat.ingestion.neml_parser import build_chunks_from_clean as neml_chunks
from rxchat.ingestion.nhia_stg_parser import build_chunks_from_clean as nhia_chunks
from rxchat.ingestion.nnmda_parser import build_chunks_from_clean as nnmda_chunks
from rxchat.ingestion.openfda_parser import parse_openfda
from rxchat.ingestion.who_parser import build_chunks_from_clean as who_chunks


UPLOAD_CHUNK_BUILDERS = {
    "neml": neml_chunks,
    "nhia_stg": nhia_chunks,
    "who": who_chunks,
    "nnmda": nnmda_chunks,
    "emdex": emdex_chunks,
}

ALL_SOURCES = ["nafdac", "openfda", "neml", "nhia_stg", "who", "nnmda", "emdex"]


class Command(BaseCommand):
    help = (
        "Build DrugChunk rows from accepted CleanData records. "
        "Scraper sources (nafdac/openfda) run their own chunking via parse_*. "
        "Upload sources (neml/nhia_stg/who/nnmda/emdex) use the stored raw_text. "
        "Run 'python manage.py seed_qdrant' afterwards to embed and sync to Qdrant."
    )

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Process all sources.")
        parser.add_argument("--source", choices=ALL_SOURCES, help="Process a single source.")

    def handle(self, *args, **options):
        if not options.get("all") and not options.get("source"):
            raise CommandError("Use --all or --source <name>.")

        selected = ALL_SOURCES if options.get("all") else [options["source"]]
        total_chunks = 0

        for source in selected:
            count = self._process_source(source)
            total_chunks += count
            self.stdout.write(f"{source}: {count} chunk(s) written")

        unembedded = DrugChunk.objects.filter(
            clean_data__source__in=selected,
            qdrant_point_id__isnull=True,
        ).count()
        self.stdout.write(self.style.SUCCESS(
            f"ingest_drugs complete — {total_chunks} total chunks. "
            f"{unembedded} unembedded. Run 'python manage.py seed_qdrant' to sync."
        ))

    def _process_source(self, source: str) -> int:
        if source == "nafdac":
            _, chunks = parse_nafdac()
            return len(chunks)

        if source == "openfda":
            _, chunks = parse_openfda(curated=True)
            return len(chunks)

        # Upload-based sources: iterate accepted CleanData records.
        builder = UPLOAD_CHUNK_BUILDERS[source]
        accepted = CleanData.objects.filter(source=source, status=CleanData.STATUS_ACCEPTED)
        if not accepted.exists():
            self.stdout.write(f"{source}: no accepted records — skipping.")
            return 0

        chunk_count = 0
        for clean in accepted:
            chunks = builder(clean)
            saved = replace_chunks(clean, chunks)
            chunk_count += len(saved)
            clean.status = CleanData.STATUS_CHUNKED
            clean.save(update_fields=["status", "updated_at"])

        return chunk_count
