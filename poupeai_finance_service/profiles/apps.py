from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'poupeai_finance_service.profiles'

    def ready(self):
        try:
            import poupeai_finance_service.profiles.signals
        except ImportError:
            pass