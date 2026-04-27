from django.core.management.base import BaseCommand

from rxchat.ingestion.base import append_ingestion_log
from rxchat.ingestion.nafdac_scraper import NAFDACGreenbookScraper, NAFDAC_CATEGORIES


class Command(BaseCommand):
    help = "Scrape NAFDAC Greenbook listings and product details."

    def add_arguments(self, parser):
        parser.add_argument("--category", type=int, choices=sorted(NAFDAC_CATEGORIES))
        parser.add_argument("--resume", action="store_true")
        parser.add_argument("--details-only", action="store_true")
        parser.add_argument("--delta", action="store_true")
        parser.add_argument("--limit", type=int)

    def handle(self, *args, **options):
        scraper = NAFDACGreenbookScraper()
        try:
            result = scraper.run(
                category=options.get("category"),
                resume=options.get("resume", False),
                details_only=options.get("details_only", False),
                delta=options.get("delta", False),
                limit=options.get("limit"),
            )
        except Exception as exc:
            append_ingestion_log("nafdac", "scrape", "failed", error=str(exc))
            raise
        append_ingestion_log("nafdac", "scrape", "ok", **result)
        self.stdout.write(self.style.SUCCESS(
            f"Scraped NAFDAC: {result['listing_count']} listings, {result['detail_count']} details."
        ))
