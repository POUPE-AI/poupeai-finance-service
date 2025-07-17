from django.contrib import admin
from poupeai_finance_service.bank_accounts.models import BankAccount

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'profile', 'initial_balance', 'is_default')
    search_fields = ('name', 'profile__email', 'profile__first_name', 'profile__last_name')
    list_filter = ('is_default', 'profile__email')

