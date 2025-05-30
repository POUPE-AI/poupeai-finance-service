from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction as db_transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import calendar
import uuid

from poupeai_finance_service.transactions.services import TransactionService
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

    def validate_profile_related_objects(self, profile, category, bank_account, credit_card):
        if category and category.profile != profile:
            raise serializers.ValidationError({"category": _("Category does not belong to your profile.")})
        if bank_account and bank_account.profile != profile:
            raise serializers.ValidationError({"bank_account": _("Bank account does not belong to your profile.")})
        if credit_card and credit_card.profile != profile:
            raise serializers.ValidationError({"credit_card": _("Credit card does not belong to your profile.")})


    def validate(self, data):
        if not self.instance and 'profile' not in data:
            data['profile'] = self.context['request'].user.profile
        
        profile = data.get('profile') or (self.instance and self.instance.profile)

        self.validate_profile_related_objects(
            profile,
            data.get('category'),
            data.get('bank_account'),
            data.get('credit_card')
        )

        source_type = data.get('source_type')
        bank_account = data.get('bank_account')
        credit_card = data.get('credit_card')
        is_installment = data.get('is_installment', False)

        if source_type == 'BANK_ACCOUNT':
            if credit_card:
                raise serializers.ValidationError({"credit_card": _("Credit card cannot be set for bank account transactions.")})
                raise serializers.ValidationError(_("Installment fields cannot be set for bank account transactions."))

        elif source_type == 'CREDIT_CARD':
            if bank_account:
                raise serializers.ValidationError({"bank_account": _("Bank account cannot be set for credit card transactions.")})
            if not credit_card:
                raise serializers.ValidationError({"credit_card": _("Credit card is required for credit card transactions.")})
            
            if is_installment:
                if not data.get('total_installments'):
                    raise serializers.ValidationError({"total_installments": _("Total installments is required for installment transactions.")})
                if not data.get('installment_number'):
                    raise serializers.ValidationError({"installment_number": _("Installment number is required for installment transactions.")})
            else:
                if data.get('total_installments') is not None or data.get('installment_number') is not None:
                    raise serializers.ValidationError(_("Installment specific fields should be null if not an installment."))
        else:
            raise serializers.ValidationError({"source_type": _("Invalid source type.")})

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
    Delegates complex logic to TransactionService.
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
            'installment_number': {'required': False, 'allow_null': True},
            'total_installments': {'required': False, 'allow_null': True},
            'original_purchase_description': {'required': False, 'allow_null': True},
            'original_transaction_id': {'required': False, 'allow_null': True},
            'original_statement_description': {'required': False, 'allow_null': True},
            'attachment': {'required': False, 'allow_null': True},
            'bank_account': {'required': False, 'allow_null': True},
            'credit_card': {'required': False, 'allow_null': True},
            'is_installment': {'required': False},
            'source_type': {'read_only': True}
        }
    
    def validate(self, data):
        data = super().validate(data)
        return data

    def create(self, validated_data):
        profile = validated_data['profile']
        apply_to_all_installments = validated_data.pop('apply_to_all_installments', False)

        try:
            return TransactionService.create_transaction(profile, validated_data)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    def update(self, instance, validated_data):
        apply_to_all_installments = validated_data.pop('apply_to_all_installments', False)

        try:
            return TransactionService.update_transaction(instance, validated_data, apply_to_all_installments)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)