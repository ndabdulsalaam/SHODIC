from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from rxchat.models import DrugChunk, SOURCE_CHOICES
from rxchat.qdrant_service import (
    ensure_collection,
    is_protected_collection,
    reset_collection,
    upsert_drug_chunks,
)


class Command(BaseCommand):
    help = "Rebuild the staging Qdrant collection from a small sample of staging DrugChunk rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=250,
            help="Maximum chunks to index. Use 0 to index all matching chunks.",
        )
        parser.add_argument(
            "--source",
            action="append",
            choices=sorted(code for code, _label in SOURCE_CHOICES),
            help="Restrict to one source. Can be passed more than once.",
        )
        parser.add_argument("--batch-size", type=int, default=64)
        parser.add_argument(
            "--keep-existing",
            action="store_true",
            help="Do not reset the staging collection before upserting the sample.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many chunks would be indexed without touching Qdrant.",
        )

    def handle(self, *args, **options):
        self._require_staging_environment()

        chunks = (
            DrugChunk.objects.exclude(text="")
            .select_related("raw_source")
            .order_by("raw_source__source", "raw_source__source_id", "chunk_index")
        )
        if options["source"]:
            chunks = chunks.filter(raw_source__source__in=options["source"])

        total = chunks.count()
        limit = options["limit"]
        selected = chunks if limit <= 0 else chunks[:limit]
        selected_count = total if limit <= 0 else min(total, limit)

        if options["dry_run"]:
            self.stdout.write(
                f"Would index {selected_count} of {total} staging chunks "
                f"into '{settings.QDRANT_COLLECTION}'."
            )
            return

        try:
            if options["keep_existing"]:
                ensure_collection()
            else:
                reset_collection()
            upserted = upsert_drug_chunks(selected, batch_size=options["batch_size"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Staging Qdrant reseed complete: {upserted} of {total} chunks "
            f"indexed into '{settings.QDRANT_COLLECTION}'."
        ))

    def _require_staging_environment(self):
        env_name = getattr(settings, "DJANGO_ENV", "").lower()
        collection = settings.QDRANT_COLLECTION
        if env_name != "staging":
            raise CommandError(
                f"reseed_staging only runs with DJANGO_ENV=staging. Current environment is '{env_name}'."
            )
        if "staging" not in collection.lower():
            raise CommandError(
                f"Refusing to reseed collection '{collection}' because it does not look like staging."
            )
        if is_protected_collection(collection):
            raise CommandError(
                f"Refusing to reseed protected Qdrant collection '{collection}'."
            )
