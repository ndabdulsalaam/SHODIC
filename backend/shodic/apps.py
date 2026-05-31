from django.apps import AppConfig


class ShodicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shodic'
    verbose_name = 'SHODIC'

    def ready(self):
        import shodic.signals  # noqa: F401, PLC0415
