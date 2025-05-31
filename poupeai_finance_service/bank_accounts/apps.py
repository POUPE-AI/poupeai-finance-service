from django.apps import AppConfig


class BankAccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'poupeai_finance_service.bank_accounts'

    def ready(self):
        import poupeai_finance_service.bank_accounts.signals