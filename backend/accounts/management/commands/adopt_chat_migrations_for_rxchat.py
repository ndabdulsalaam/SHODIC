from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = (
        "One-time deployment helper: mark previously applied chat migrations "
        "as rxchat migrations before running migrate."
    )

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names(cursor)
            if "django_migrations" not in tables:
                self.stdout.write("No django_migrations table found; nothing to adopt.")
                return

            cursor.execute("SELECT name FROM django_migrations WHERE app = %s", ["chat"])
            names = [row[0] for row in cursor.fetchall()]

            if not names:
                self.stdout.write("No chat migration records found; nothing to adopt.")
                return

            adopted = 0
            removed_duplicates = 0
            with transaction.atomic():
                for name in names:
                    cursor.execute(
                        "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
                        ["rxchat", name],
                    )
                    if cursor.fetchone():
                        cursor.execute(
                            "DELETE FROM django_migrations WHERE app = %s AND name = %s",
                            ["chat", name],
                        )
                        removed_duplicates += 1
                    else:
                        cursor.execute(
                            "UPDATE django_migrations SET app = %s WHERE app = %s AND name = %s",
                            ["rxchat", "chat", name],
                        )
                        adopted += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Adopted {adopted} chat migration record(s) for rxchat; "
                    f"removed {removed_duplicates} duplicate old record(s)."
                )
            )
