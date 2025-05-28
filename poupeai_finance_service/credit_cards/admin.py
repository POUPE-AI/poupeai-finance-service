from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from poupeai_finance_service.credit_cards.models import CreditCard

@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ('profile', 'name', 'brand', 'credit_limit', 'closing_day', 'due_day', 'created_at', 'updated_at')
    list_filter = ('brand', 'profile')
    search_fields = ('name', 'profile__user__username')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('profile', 'name', 'brand', 'credit_limit', 'additional_info')
        }),
        (_('Invoicing Dates'), {
            'fields': ('closing_day', 'due_day')
        }),
        (_('Audit Data'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )