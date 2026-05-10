from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from rxchat.models import DrugChunk, SOURCE_CHOICES
from rxchat.qdrant_service import (
    ensure_collection,
    is_protected_collection,
    upsert_drug_chunks,
)


class Command(BaseCommand):
    help = (
        "Sync DrugChunk rows from Postgres into the active Qdrant collection. "
        "By default only upserts chunks not yet embedded (qdrant_point_id is NULL). "
        "Use --all to force a full resync of every chunk. "
        "Duplicate-safe: Qdrant point IDs are derived from chunk PKs, so re-upserting "
        "the same chunk overwrites rather than duplicates."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Upsert every DrugChunk, not just unembedded ones.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum chunks to index. 0 means no limit.",
        )
        parser.add_argument(
            "--source",
            action="append",
            choices=sorted(code for code, _label in SOURCE_CHOICES),
            help="Restrict to one or more sources.",
        )
        parser.add_argument("--batch-size", type=int, default=64)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many chunks would be indexed without touching Qdrant.",
        )

    def handle(self, *args, **options):
        self._refuse_production()

        chunks = (
            DrugChunk.objects.exclude(text="")
            .filter(clean_data__isnull=False)
            .select_related("clean_data")
            .order_by("clean_data__source", "clean_data__source_id", "chunk_index")
        )

        if not options["all"]:
            chunks = chunks.filter(qdrant_point_id__isnull=True)

        if options["source"]:
            chunks = chunks.filter(clean_data__source__in=options["source"])

        total = chunks.count()
        limit = options["limit"]
        selected = chunks if limit <= 0 else chunks[:limit]
        selected_count = total if limit <= 0 else min(total, limit)

        if total == 0:
            self.stdout.write("No chunks to sync — everything is up to date.")
            return

        if options["dry_run"]:
            mode = "all" if options["all"] else "unembedded only"
            self.stdout.write(
                f"Would index {selected_count} of {total} chunks ({mode}) "
                f"into '{settings.QDRANT_COLLECTION}'."
            )
            return

        ensure_collection()

        try:
            upserted = upsert_drug_chunks(selected, batch_size=options["batch_size"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        mode = "full resync" if options["all"] else "incremental"
        self.stdout.write(self.style.SUCCESS(
            f"Qdrant seed complete ({mode}): {upserted} of {total} chunks "
            f"indexed into '{settings.QDRANT_COLLECTION}'."
        ))

    def _refuse_production(self):
        collection = settings.QDRANT_COLLECTION
        if is_protected_collection(collection):
            raise CommandError(
                f"Refusing to seed protected Qdrant production collection '{collection}'."
            )
