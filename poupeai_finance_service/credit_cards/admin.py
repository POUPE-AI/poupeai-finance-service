from django.contrib import admin
from poupeai_finance_service.credit_cards.models import CreditCard

@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ('profile', 'name', 'brand', 'credit_limit', 'closing_day', 'due_day', 'created_at')
    list_filter = ('brand', 'profile')
    search_fields = ('name', 'profile__user__username')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('profile', 'name', 'brand', 'credit_limit', 'additional_info')
        }),
        ('Datas de Faturamento', {
            'fields': ('closing_day', 'due_day')
        }),
        ('Informações de Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )