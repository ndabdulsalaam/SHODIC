from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from rxchat.qdrant_service import is_protected_collection, reset_collection


class Command(BaseCommand):
    help = "Delete and recreate the active Qdrant collection. Refuses production."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm that the active non-production collection should be reset.",
        )

    def handle(self, *args, **options):
        collection = settings.QDRANT_COLLECTION
        if is_protected_collection(collection):
            raise CommandError(
                f"Refusing to reset protected Qdrant collection '{collection}'."
            )
        if not options["yes"]:
            raise CommandError(
                f"This will delete all points in '{collection}'. Re-run with --yes to confirm."
            )

        try:
            reset_collection()
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Qdrant collection '{collection}' reset for {settings.DJANGO_ENV}."
        ))
