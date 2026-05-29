from django.core.management.base import BaseCommand, CommandError

from shodic.models import DrugChunk, SourceFileUpload
from shodic.ingestion.base import append_ingestion_log
from shodic.ingestion.emdex_parser import parse_emdex
from shodic.ingestion.nafdac_parser import parse_nafdac
from shodic.ingestion.neml_parser import parse_neml
from shodic.ingestion.nhia_stg_parser import parse_nhia_stg
from shodic.ingestion.nnmda_parser import parse_nnmda
from shodic.ingestion.openfda_parser import parse_openfda
from shodic.ingestion.who_parser import parse_who_eml
from shodic.qdrant_service import upsert_drug_chunks


PARSERS = {
    "nafdac": parse_nafdac,
    "openfda": lambda: parse_openfda(curated=True),
    "neml": parse_neml,
    "nhia_stg": parse_nhia_stg,
    "who": parse_who_eml,
    "nnmda": parse_nnmda,
    "emdex": parse_emdex,
}


class Command(BaseCommand):
    help = "Parse drug sources into RAG chunks and optionally upsert to Qdrant."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--source", choices=sorted(PARSERS))
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--skip-qdrant", action="store_true")

    def handle(self, *args, **options):
        if not options.get("all") and not options.get("source"):
            raise CommandError("Use --all or --source <name>.")

        selected = list(PARSERS) if options.get("all") else [options["source"]]
        parsed_counts = {}
        for source in selected:
            records, chunks = PARSERS[source]()
            parsed_counts[source] = {"records": len(records), "chunks": len(chunks)}
            self.stdout.write(f"{source}: {len(records)} records, {len(chunks)} chunks")

        upserted = 0
        db_chunks = DrugChunk.objects.filter(raw_source__source__in=selected).select_related("raw_source")
        if not options.get("dry_run") and not options.get("skip_qdrant") and db_chunks.exists():
            upserted = upsert_drug_chunks(db_chunks)
            SourceFileUpload.objects.filter(source__in=selected, processed=False).update(processed=True)

        status = "dry_run" if options.get("dry_run") else "ok"
        append_ingestion_log("all", "ingest_drugs", status, parsed_counts=parsed_counts, upserted=upserted)
        self.stdout.write(self.style.SUCCESS(
            f"Ingestion complete: {db_chunks.count()} stored chunks, {upserted} upserted."
        ))
