from django.db import transaction as db_transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from poupeai_finance_service.transactions.models import Transaction
from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.credit_cards.models import Invoice

class TransactionService:
    @staticmethod
    @db_transaction.atomic
    def create_transaction(profile, data):
        source_type = data.get('source_type')
        is_installment = data.get('is_installment', False)
        category = data.get('category')

        if not profile:
            raise DjangoValidationError(_("Profile is required."))

        data['profile'] = profile
        if category:
            data['type'] = category.type

        if source_type == 'BANK_ACCOUNT' and not data.get('bank_account'):
            default_bank_account = BankAccount.objects.filter(profile=profile, is_default=True).first()
            if default_bank_account:
                data['bank_account'] = default_bank_account
            else:
                raise DjangoValidationError({"bank_account": _("Bank account is required for bank account transactions or a default bank account must be set.")})

        if source_type == 'CREDIT_CARD' and is_installment:
            transactions = Transaction.objects.create_installment_transactions(**data)
            return transactions[0] if transactions else None
        else:
            if source_type == 'CREDIT_CARD' and 'transaction_date' in data:
                credit_card = data.get('credit_card')
                if credit_card:
                    data['invoice'] = Invoice.objects.get_or_create_invoice(
                        credit_card=credit_card,
                        transaction_date=data['transaction_date']
                    )

            transaction_instance = Transaction(**data)
            transaction_instance.full_clean()
            transaction_instance.save()
            return transaction_instance

    @staticmethod
    @db_transaction.atomic
    def update_transaction(instance, data, apply_to_all_installments=False):
        if 'source_type' in data and data['source_type'] != instance.source_type:
            raise DjangoValidationError(
                {"source_type": _("Cannot change transaction source type after creation.")}
            )

        if instance.source_type == 'CREDIT_CARD' and 'transaction_date' in data:
            raise DjangoValidationError(
                {"transaction_date": _("Cannot change transaction date for credit card transactions.")}
            )

        if instance.source_type == 'CREDIT_CARD' and 'credit_card' in data:
            raise DjangoValidationError(
                {"credit_card": _("Cannot change credit card for credit card transactions.")}
            )
        
        if 'category' in data and data['category']:
            data['type'] = data['category'].type
        
        if instance.source_type == 'CREDIT_CARD' and instance.is_installment:
            restricted_fields = [
                'total_installments', 'is_installment',
                'purchase_group_uuid'
            ]
            for field in restricted_fields:
                if field in data and data[field] != getattr(instance, field):
                    raise DRFValidationError(
                        {field: _(f"Cannot change {field.replace('_', ' ')} for installment transaction.")}
                    )

            if apply_to_all_installments:
                updated_fields = {}
                if 'category' in data and data['category'] != instance.category:
                    updated_fields['category'] = data['category']
                    updated_fields['type'] = data['category'].type
                if 'amount' in data and data['amount'] != instance.amount:
                    updated_fields['amount'] = data['amount']
                
                if updated_fields:
                    Transaction.objects.filter(
                        purchase_group_uuid=instance.purchase_group_uuid
                    ).update(**updated_fields)
                    instance.refresh_from_db()
            else:
                for attr, value in data.items():
                    if attr == 'description':
                        setattr(instance, attr, value)
                    elif attr not in restricted_fields:
                        setattr(instance, attr, value)
                
                instance.full_clean()
                instance.save()
        else:
            for attr, value in data.items():
                setattr(instance, attr, value)
            
            instance.full_clean()
            instance.save()

        return instance
    
    @staticmethod
    @db_transaction.atomic
    def delete_transaction(instance, deletion_option=None):
        """
        Improved deletion logic for installments:
        - Updates remaining installments' numbers and descriptions
        - Maintains data consistency
        """
        if instance.source_type == 'CREDIT_CARD' and instance.is_installment:
            if deletion_option is None:
                raise DRFValidationError(
                    _("For installment transactions, 'deletion_option' must be provided.")
                )
            
            purchase_group = Transaction.objects.filter(
                purchase_group_uuid=instance.purchase_group_uuid
            ).order_by('installment_number')

            if deletion_option == 'CURRENT_ONLY':
                instance.delete()
                remaining = purchase_group.exclude(id=instance.id)
                
                for idx, trans in enumerate(remaining, start=1):
                    trans.installment_number = idx
                    original_desc = trans.original_purchase_description or trans.description.split(' (')[0]
                    trans.description = f"{original_desc} ({idx}/{remaining.count()})"
                    trans.save()

                remaining.update(total_installments=remaining.count())

            elif deletion_option == 'CURRENT_AND_FUTURE':
                to_delete = purchase_group.filter(
                    installment_number__gte=instance.installment_number
                )
                to_delete.delete()
                
                remaining = purchase_group.filter(
                    installment_number__lt=instance.installment_number
                )
                
                if remaining.exists():
                    remaining.update(total_installments=remaining.count())
            else:
                raise DRFValidationError(
                    _("Invalid deletion_option. Use 'CURRENT_ONLY' or 'CURRENT_AND_FUTURE'.")
                )
        else:
            instance.delete()
