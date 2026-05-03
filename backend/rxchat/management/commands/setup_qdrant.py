from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from rxchat.qdrant_service import collection_config, ensure_collection


class Command(BaseCommand):
    help = "Create the active environment's Qdrant collection if it does not exist."

    def handle(self, *args, **options):
        try:
            created = ensure_collection()
            config = collection_config()
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        dense = config["vectors_config"][settings.QDRANT_DENSE_VECTOR_NAME]
        action = "created" if created else "already exists"
        self.stdout.write(self.style.SUCCESS(
            f"Qdrant collection '{settings.QDRANT_COLLECTION}' {action} "
            f"for {settings.DJANGO_ENV}: "
            f"dense='{settings.QDRANT_DENSE_VECTOR_NAME}' size={dense.size} "
            f"distance={dense.distance}, "
            f"sparse='{settings.QDRANT_SPARSE_VECTOR_NAME}'."
        ))
