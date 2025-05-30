from django.db import transaction as db_transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError

from poupeai_finance_service.transactions.models import Transaction
from poupeai_finance_service.bank_accounts.models import BankAccount

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
            transaction_instance = Transaction(**data)
            transaction_instance.full_clean()
            transaction_instance.save()
            return transaction_instance

    @staticmethod
    @db_transaction.atomic
    def update_transaction(instance, data, apply_to_all_installments=False):
        if 'source_type' in data and data['source_type'] != instance.source_type:
            raise DjangoValidationError({"source_type": _("Source type cannot be changed after creation.")})
        
        if instance.source_type == 'CREDIT_CARD' and instance.is_installment:
            restricted_installment_fields = [
                'total_installments', 'transaction_date', 'is_installment',
                'purchase_group_uuid', 'invoice', 'credit_card'
            ]
            for field in restricted_installment_fields:
                if field in data and data[field] != getattr(instance, field):
                    raise DjangoValidationError({field: _(f"{field.replace('_', ' ').title()} cannot be changed for an installment transaction.")})

            if apply_to_all_installments:
                updated_fields = {}
                if 'category' in data and data['category'] != instance.category:
                    updated_fields['category'] = data['category']
                    updated_fields['type'] = data['category'].type
                if 'amount' in data and data['amount'] != instance.amount:
                    updated_fields['amount'] = data['amount']
                if 'description' in data and data['description'] != instance.description:
                    updated_fields['original_purchase_description'] = data['description']
                
                if updated_fields:
                    Transaction.objects.filter(purchase_group_uuid=instance.purchase_group_uuid).update(
                        **updated_fields,
                        updated_at=timezone.now()
                    )
                    instance.refresh_from_db()
            else:
                for attr, value in data.items():
                    setattr(instance, attr, value)
                
                if 'category' in data:
                    instance.type = instance.category.type
                
                instance.full_clean()
                instance.save()
        else:
            if 'category' in data:
                data['type'] = data['category'].type
            
            for attr, value in data.items():
                setattr(instance, attr, value)
            
            instance.full_clean()
            instance.save()

        return instance
    
    @staticmethod
    @db_transaction.atomic
    def delete_transaction(instance, deletion_option=None):
        """
        Handles the deletion of a transaction, including installment logic.
        deletion_option: 'CURRENT_ONLY' or 'CURRENT_AND_FUTURE' for installments.
        """
        if instance.source_type == 'CREDIT_CARD' and instance.is_installment:
            if deletion_option is None:
                raise DjangoValidationError(
                    _("For installment credit card transactions, 'deletion_option' must be provided ('CURRENT_ONLY' or 'CURRENT_AND_FUTURE').")
                )
            
            if deletion_option == 'CURRENT_ONLY':
                instance.delete()
                remaining_installments = Transaction.objects.filter(
                    purchase_group_uuid=instance.purchase_group_uuid,
                    installment_number__gt=instance.installment_number
                ).order_by('installment_number')

                start_number = instance.installment_number
                for i, trans in enumerate(remaining_installments):
                    trans.installment_number = start_number + i
                    trans.save(update_fields=['installment_number', 'updated_at'])

                new_total_installments = Transaction.objects.filter(purchase_group_uuid=instance.purchase_group_uuid).count()
                if new_total_installments > 0:
                    Transaction.objects.filter(purchase_group_uuid=instance.purchase_group_uuid).update(
                        total_installments=new_total_installments,
                        updated_at=timezone.now()
                    )
                else:
                    Transaction.objects.filter(purchase_group_uuid=instance.purchase_group_uuid).update(
                        total_installments=None,
                        updated_at=timezone.now()
                    )

            elif deletion_option == 'CURRENT_AND_FUTURE':
                Transaction.objects.filter(
                    purchase_group_uuid=instance.purchase_group_uuid,
                    installment_number__gte=instance.installment_number
                ).delete()
                past_installments = Transaction.objects.filter(
                    purchase_group_uuid=instance.purchase_group_uuid
                )
                if past_installments.exists():
                    new_total_installments = past_installments.count()
                    past_installments.update(total_installments=new_total_installments, updated_at=timezone.now())
                
            else:
                raise DjangoValidationError(
                    _("For installment transactions, 'deletion_option' must be either 'CURRENT_ONLY' or 'CURRENT_AND_FUTURE'.")
                )
        else:
            instance.delete()
