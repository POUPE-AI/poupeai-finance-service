from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import CreditCard, Invoice

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

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Invoice model.
    """
    list_display = (
        'credit_card',
        'month', 'year', 
        'due_date', 
        'total_amount', 
        'amount_paid', 
        'paid',
    )
    list_filter = ('paid', 'credit_card', 'year',)
    search_fields = ('credit_card__name',)
    raw_id_fields = ('credit_card',)
    readonly_fields = ('total_amount',)
    fieldsets = (
        (None, {
            'fields': (
                'credit_card',
                ('month', 'year'),
                'due_date',
                'amount_paid',
                'paid',
            )
        }),
        (_('Calculated Fields'), {
            'fields': (
                'total_amount',
            ),
            'classes': ('collapse',),
        }),
    )