from rest_framework import serializers
from django.db import transaction as db_transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import calendar
import uuid

from poupeai_finance_service.transactions.models import Transaction, Invoice
from poupeai_finance_service.categories.models import Category
from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.credit_cards.models import CreditCard

class InvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the Invoice model.
    """
    class Meta:
        model = Invoice
        fields = [
            'id', 'credit_card', 'month', 'year',
            'amount_paid', 'due_date', 'paid',
            'total_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['total_amount', 'created_at', 'updated_at']

class TransactionBaseSerializer(serializers.ModelSerializer):
    """
    Base serializer for Transaction model, used for common fields.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    type = serializers.CharField(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'profile', 'category', 'category_name', 'description',
            'amount', 'transaction_date', 'type', 'source_type',
            'bank_account', 'credit_card', 'is_installment', 'installment_number',
            'total_installments', 'purchase_group_uuid', 'original_purchase_description',
            'invoice', 'original_transaction_id', 'original_statement_description',
            'attachment', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['profile', 'type', 'status', 'purchase_group_uuid', 'invoice', 'created_at', 'updated_at']

    def validate(self, data):
        if not self.instance and 'profile' not in data:
            data['profile'] = self.context['request'].user.profile

        profile = data.get('profile') or (self.instance and self.instance.profile)

        category = data.get('category')
        if category and category.profile != profile:
            raise serializers.ValidationError({"category": _("Category does not belong to your profile.")})

        source_type = data.get('source_type')
        bank_account = data.get('bank_account')
        credit_card = data.get('credit_card')
        is_installment = data.get('is_installment', False)
        installment_number = data.get('installment_number')
        total_installments = data.get('total_installments')

        if source_type == 'BANK_ACCOUNT':
            if credit_card:
                raise serializers.ValidationError({"credit_card": _("Credit card cannot be set for bank account transactions.")})
            if is_installment or installment_number or total_installments:
                raise serializers.ValidationError(_("Installment fields cannot be set for bank account transactions."))
            if not bank_account:
                if not self.instance:
                    default_bank_account = BankAccount.objects.filter(profile=profile, is_default=True).first()
                    if default_bank_account:
                        data['bank_account'] = default_bank_account
                    else:
                        raise serializers.ValidationError({"bank_account": _("Bank account is required for bank account transactions or a default bank account must be set.")})
                else:
                    if not bank_account and self.instance.source_type == 'BANK_ACCOUNT':
                         raise serializers.ValidationError({"bank_account": _("Bank account is required for bank account transactions.")})
            elif bank_account.profile != profile:
                raise serializers.ValidationError({"bank_account": _("Bank account does not belong to your profile.")})

        elif source_type == 'CREDIT_CARD':
            if bank_account:
                raise serializers.ValidationError({"bank_account": _("Bank account cannot be set for credit card transactions.")})
            if not credit_card:
                raise serializers.ValidationError({"credit_card": _("Credit card is required for credit card transactions.")})
            elif credit_card.profile != profile:
                raise serializers.ValidationError({"credit_card": _("Credit card does not belong to your profile.")})
            
            if is_installment:
                if not total_installments or total_installments < 1:
                    raise serializers.ValidationError({"total_installments": _("Total installments must be a positive number for installment transactions.")})
                if not installment_number or not (1 <= installment_number <= total_installments):
                    raise serializers.ValidationError({"installment_number": _("Installment number must be between 1 and total installments.")})
            else:
                if total_installments is not None or installment_number is not None:
                    raise serializers.ValidationError(_("Installment specific fields should be null if not an installment."))
        else:
            raise serializers.ValidationError({"source_type": _("Invalid source type.")})

        if category:
            data['type'] = category.type

        return data

class TransactionListSerializer(TransactionBaseSerializer):
    """
    Serializer for listing transactions, showing essential fields.
    """
    bank_account_name = serializers.CharField(source='bank_account.name', read_only=True)
    credit_card_name = serializers.CharField(source='credit_card.name', read_only=True)

    class Meta(TransactionBaseSerializer.Meta):
        fields = [
            'id', 'description', 'amount', 'transaction_date',
            'type', 'source_type', 'category_name', 'status',
            'bank_account_name', 'credit_card_name'
        ]

class TransactionDetailSerializer(TransactionBaseSerializer):
    """
    Serializer for retrieving detailed transaction information.
    """
    bank_account_name = serializers.CharField(source='bank_account.name', read_only=True)
    credit_card_name = serializers.CharField(source='credit_card.name', read_only=True)
    category_type = serializers.CharField(source='category.type', read_only=True)

    class Meta(TransactionBaseSerializer.Meta):
        fields = TransactionBaseSerializer.Meta.fields + [
            'bank_account_name', 'credit_card_name', 'category_type'
        ]
        read_only_fields = TransactionBaseSerializer.Meta.read_only_fields + [
            'bank_account_name', 'credit_card_name', 'category_type'
        ]

class TransactionCreateUpdateSerializer(TransactionBaseSerializer):
    """
    Serializer for creating and updating transactions.
    Handles the logic for installment creation and specific update restrictions.
    """
    apply_to_all_installments = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta(TransactionBaseSerializer.Meta):
        fields = [
            'id', 'category', 'description', 'amount', 'transaction_date',
            'source_type', 'bank_account', 'credit_card',
            'is_installment', 'installment_number', 'total_installments',
            'original_purchase_description', 'original_transaction_id',
            'original_statement_description', 'attachment',
            'apply_to_all_installments'
        ]
        extra_kwargs = {
            'installment_number': {'required': False},
            'total_installments': {'required': False},
            'original_purchase_description': {'required': False},
            'original_transaction_id': {'required': False},
            'original_statement_description': {'required': False},
            'attachment': {'required': False},
            'bank_account': {'required': False},
            'credit_card': {'required': False},
            'is_installment': {'required': False},
        }

    def validate(self, data):
        data = super().validate(data)

        if self.instance:
            if 'source_type' in data and data['source_type'] != self.instance.source_type:
                raise serializers.ValidationError({"source_type": _("Source type cannot be changed after creation.")})
            
            if 'credit_card' in data and data['credit_card'] != self.instance.credit_card:
                raise serializers.ValidationError({"credit_card": _("Credit card cannot be changed for an existing transaction.")})

            if self.instance.source_type == 'CREDIT_CARD':
                if self.instance.is_installment:
                    restricted_installment_fields = [
                        'total_installments', 'transaction_date', 'is_installment',
                        'purchase_group_uuid', 'invoice'
                    ]
                    for field in restricted_installment_fields:
                        if field in data and data[field] != getattr(self.instance, field):
                             raise serializers.ValidationError({field: _(f"{field.replace('_', ' ').title()} cannot be changed for an installment transaction.")})
                
                if 'bank_account' in data and data['bank_account'] is not None:
                    raise serializers.ValidationError({"bank_account": _("Bank account cannot be set for credit card transactions.")})
                if 'source_type' in data and data['source_type'] == 'BANK_ACCOUNT':
                    raise serializers.ValidationError({"source_type": _("Cannot change source type from CREDIT_CARD to BANK_ACCOUNT.")})

        return data

    @db_transaction.atomic
    def create(self, validated_data):
        apply_to_all_installments = validated_data.pop('apply_to_all_installments', False)

        profile = validated_data['profile']
        source_type = validated_data['source_type']
        is_installment = validated_data.get('is_installment', False)

        if source_type == 'CREDIT_CARD' and is_installment:
            credit_card = validated_data['credit_card']
            total_installments = validated_data['total_installments']
            transaction_date = validated_data['transaction_date']
            original_purchase_description = validated_data.get('description')

            purchase_group_uuid = uuid.uuid4()

            transactions = []
            for i in range(1, total_installments + 1):
                installment_transaction_date = self._calculate_installment_date(transaction_date, i-1)
                invoice = self._get_or_create_invoice(
                    credit_card=credit_card,
                    transaction_date=installment_transaction_date
                )

                installment_data = {
                    **validated_data,
                    'profile': profile,
                    'is_installment': True,
                    'installment_number': i,
                    'total_installments': total_installments,
                    'purchase_group_uuid': purchase_group_uuid,
                    'original_purchase_description': original_purchase_description,
                    'transaction_date': installment_transaction_date,
                    'invoice': invoice,
                    'description': f"{original_purchase_description} ({i}/{total_installments})",
                }
                transaction_instance = Transaction(**installment_data)
                transaction_instance.full_clean()
                transaction_instance.save()
                transactions.append(transaction_instance)
            
            return transactions[0] if transactions else super().create(validated_data)
        else:
            validated_data['type'] = validated_data['category'].type
            return super().create(validated_data)

    @db_transaction.atomic
    def update(self, instance, validated_data):
        
        apply_to_all_installments = validated_data.pop('apply_to_all_installments', False)

        if instance.source_type == 'CREDIT_CARD' and instance.is_installment:
            if apply_to_all_installments:
                updated_fields = {}
                if 'category' in validated_data and validated_data['category'] != instance.category:
                    updated_fields['category'] = validated_data['category']
                    updated_fields['type'] = validated_data['category'].type
                if 'amount' in validated_data and validated_data['amount'] != instance.amount:
                    updated_fields['amount'] = validated_data['amount']
                if 'description' in validated_data and validated_data['description'] != instance.description:
                    updated_fields['original_purchase_description'] = validated_data['description']
                
                if updated_fields:
                    Transaction.objects.filter(purchase_group_uuid=instance.purchase_group_uuid).update(
                        **updated_fields,
                        updated_at=timezone.now()
                    )
                    instance.refresh_from_db()
            else:
                if 'category' in validated_data and validated_data['category'] != instance.category:
                    instance.category = validated_data['category']
                    instance.type = validated_data['category'].type
                if 'amount' in validated_data and validated_data['amount'] != instance.amount:
                    instance.amount = validated_data['amount']
                if 'description' in validated_data and validated_data['description'] != instance.description:
                    instance.description = validated_data['description']
                for attr, value in validated_data.items():
                    if attr not in ['category', 'amount', 'description']:
                        setattr(instance, attr, value)
                instance.save()
        else:
            if 'category' in validated_data:
                validated_data['type'] = validated_data['category'].type
            
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

        return instance

    def _calculate_installment_date(self, base_date, installment_offset):
        """
        Calculates the date for a given installment.
        Adjusts month and year if needed.
        """
        year = base_date.year
        month = base_date.month + installment_offset

        while month > 12:
            month -= 12
            year += 1
        
        last_day_of_month = calendar.monthrange(year, month)[1]
        day = min(base_date.day, last_day_of_month)

        return base_date.replace(year=year, month=month, day=day)

    def _get_or_create_invoice(self, credit_card, transaction_date):
        """
        Gets or creates an invoice for the given credit card and transaction date.
        Assumes invoice due_day is credit_card.due_day for that month/year.
        """
        invoice_month = transaction_date.month
        invoice_year = transaction_date.year

        last_day_of_invoice_month = calendar.monthrange(invoice_year, invoice_month)[1]
        due_day = min(credit_card.due_day, last_day_of_invoice_month)
        invoice_due_date = transaction_date.replace(year=invoice_year, month=invoice_month, day=due_day)

        invoice, created = Invoice.objects.get_or_create(
            credit_card=credit_card,
            month=invoice_month,
            year=invoice_year,
            defaults={'due_date': invoice_due_date}
        )
        return invoice