from django.apps import AppConfig


class CaisseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'caisse'
    verbose_name = 'Caisse'

    def ready(self):
        import caisse.signals  # noqa: F401
