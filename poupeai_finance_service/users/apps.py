from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'poupeai_finance_service.users'

    def ready(self):
        import users.signals