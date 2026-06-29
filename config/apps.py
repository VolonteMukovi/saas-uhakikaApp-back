"""Configuration Django — hooks au démarrage (manifeste CURSOR.md)."""
from django.apps import AppConfig


class ConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'
    label = 'uhakika_config'
    verbose_name = 'Configuration HTTP Uhakika'

    def ready(self):
        from config.http.preconditions import apply_precondition_patches
        apply_precondition_patches()
