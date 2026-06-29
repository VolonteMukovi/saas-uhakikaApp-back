from django.apps import AppConfig


class AbonnementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'abonnements'
    verbose_name = 'Abonnements SaaS'

    def ready(self):
        import abonnements.signals  # noqa: F401
