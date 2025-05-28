from django.contrib import admin
from poupeai_finance_service.bank_accounts.models import BankAccount

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'profile', 'initial_balance')
    search_fields = ('name', 'profile__user__username')
    list_filter = ('profile__user__username',)

