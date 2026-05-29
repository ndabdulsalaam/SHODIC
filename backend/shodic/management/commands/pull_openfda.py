from django.core.management.base import BaseCommand

from shodic.ingestion.base import append_ingestion_log
from shodic.ingestion.openfda_puller import OpenFDAPuller


class Command(BaseCommand):
    help = "Pull OpenFDA drug labels."

    def add_arguments(self, parser):
        parser.add_argument("--curated", action="store_true")
        parser.add_argument("--resume", action="store_true")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--recent-days", type=int)

    def handle(self, *args, **options):
        puller = OpenFDAPuller()
        try:
            result = puller.pull(
                curated=options.get("curated", False),
                resume=options.get("resume", False),
                limit=options.get("limit"),
                recent_days=options.get("recent_days"),
            )
        except Exception as exc:
            append_ingestion_log("openfda", "pull", "failed", error=str(exc))
            raise
        append_ingestion_log("openfda", "pull", "ok", **result)
        self.stdout.write(self.style.SUCCESS(
            f"Pulled OpenFDA ({result['mode']}): {result['pulled_records']} records."
        ))

