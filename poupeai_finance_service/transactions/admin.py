from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Transaction model.
    """
    list_display = (
        'description',
        'profile',
        'category',
        'amount',
        'issue_date',
        'type',
        'source_type',
        'bank_account',
        'credit_card',
        'is_installment',
        'installment_number',
        'total_installments',
        'status',
    )
    list_filter = (
        'source_type',
        'type',
        'is_installment',
        'category',
        'profile',
        'issue_date',
    )
    search_fields = (
        'description',
        'profile__email',
        'category__name',
        'bank_account__name',
        'credit_card__name',
    )
    raw_id_fields = (
        'profile',
        'category',
        'bank_account',
        'credit_card',
        'invoice',
    )
    readonly_fields = (
        'type',
        'status',
        'purchase_group_uuid',
    )

    fieldsets = (
        (None, {
            'fields': (
                'profile',
                'category',
                'description',
                'amount',
                'issue_date',
                'source_type',
            )
        }),
        (_('Source Details'), {
            'fields': (
                'bank_account',
                'credit_card',
            ),
            'description': _('Select either a Bank Account or a Credit Card.'),
        }),
        (_('Installment Details'), {
            'fields': (
                'is_installment',
                'installment_number',
                'total_installments',
                'original_purchase_description',
            ),
            'classes': ('collapse',),
        }),
        (_('Credit Card Invoice'), {
            'fields': (
                'invoice',
            ),
            'classes': ('collapse',),
            'description': _('Only applicable for credit card transactions linked to an invoice.'),
        }),
        (_('Additional Information'), {
            'fields': (
                'original_transaction_id',
                'original_statement_description',
                'attachment',
                'purchase_group_uuid',
            ),
            'classes': ('collapse',),
        }),
        (_('System Generated'), {
            'fields': (
                'type',
                'status',
            ),
            'classes': ('collapse',),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """
        Custom form to handle conditional display of fields based on 'source_type'.
        """
        form = super().get_form(request, obj, **kwargs)
        if obj:
            if obj.source_type == 'BANK_ACCOUNT':
                form.base_fields['credit_card'].widget.can_add_related = False
                form.base_fields['credit_card'].widget.can_change_related = False
                form.base_fields['invoice'].widget.can_add_related = False
                form.base_fields['invoice'].widget.can_change_related = False
                form.base_fields['is_installment'].widget.can_add_related = False
                form.base_fields['is_installment'].widget.can_change_related = False
                form.base_fields['installment_number'].widget.can_add_related = False
                form.base_fields['installment_number'].widget.can_change_related = False
                form.base_fields['total_installments'].widget.can_add_related = False
                form.base_fields['total_installments'].widget.can_change_related = False
                form.base_fields['original_purchase_description'].widget.can_add_related = False
                form.base_fields['original_purchase_description'].widget.can_change_related = False
            elif obj.source_type == 'CREDIT_CARD':
                form.base_fields['bank_account'].widget.can_add_related = False
                form.base_fields['bank_account'].widget.can_change_related = False
        return form

    def get_queryset(self, request):
        """
        Optimize queryset for list display.
        """
        return super().get_queryset(request).select_related(
            'profile__user', 'category', 'bank_account', 'credit_card', 'invoice'
        )