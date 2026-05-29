from django.core.management.base import BaseCommand, CommandError

from shodic.ingestion.update_checker import schedule_defaults


class Command(BaseCommand):
    help = "Create default Django-Q2 schedules for SHODIC ingestion."

    def handle(self, *args, **options):
        try:
            from django_q.models import Schedule  # noqa: PLC0415
        except ImportError as exc:
            raise CommandError("django-q2 is not installed. Run pip install -r requirements.txt.") from exc

        created = 0
        updated = 0
        for item in schedule_defaults():
            schedule_type = item["schedule_type"]
            if schedule_type == "W":
                schedule_type = Schedule.WEEKLY
            elif schedule_type == "M":
                schedule_type = Schedule.MONTHLY
            elif schedule_type == "Y":
                schedule_type = Schedule.YEARLY
            _, was_created = Schedule.objects.update_or_create(
                name=item["name"],
                defaults={
                    "func": item["func"],
                    "args": item["args"],
                    "schedule_type": schedule_type,
                    "repeats": -1,
                    "next_run": item["next_run"],
                },
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(
            f"Ingestion schedules ready: {created} created, {updated} updated."
        ))

