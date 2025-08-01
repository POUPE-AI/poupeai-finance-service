from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from poupeai_finance_service.transactions.models import Transaction
from poupeai_finance_service.transactions.services import TransactionService

class TransactionBaseSerializer(serializers.ModelSerializer):
    """
    Base serializer for Transaction model, used for common fields.
    """
    type = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False)

    class Meta:
        model = Transaction
        fields = [
            'id', 'profile', 'category', 'description',
            'amount', 'issue_date', 'type', 'source_type',
            'bank_account', 'credit_card', 'is_installment', 'installment_number',
            'total_installments', 'purchase_group_uuid', 'original_purchase_description',
            'invoice', 'original_transaction_id', 'original_statement_description',
            'attachment', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['profile', 'type', 'status', 'purchase_group_uuid', 'invoice', 'created_at', 'updated_at']

    def validate_category(self, category):
        if not category:
            return category
            
        profile = self.context.get('request').user if self.context.get('request') else None
        if self.instance:
            profile = profile or self.instance.profile
            
        if profile and category.profile != profile:
            raise serializers.ValidationError(_("Category does not belong to your profile."))
        return category
    
    def validate_bank_account(self, bank_account):
        if not bank_account:
            return bank_account
            
        profile = self.context.get('request').user if self.context.get('request') else None
        if self.instance:
            profile = profile or self.instance.profile
            
        if profile and bank_account.profile != profile:
            raise serializers.ValidationError(_("Bank account does not belong to your profile."))
        return bank_account
    
    def validate_credit_card(self, credit_card):
        if not credit_card:
            return credit_card
            
        profile = self.context.get('request').user if self.context.get('request') else None
        if self.instance:
            profile = profile or self.instance.profile
            
        if profile and credit_card.profile != profile:
            raise serializers.ValidationError(_("Credit card does not belong to your profile."))
        return credit_card

    def validate(self, data):
        if not self.instance and 'profile' not in data:
            data['profile'] = self.context['request'].user

        source_type = data.get('source_type')
        bank_account = data.get('bank_account')
        credit_card = data.get('credit_card')
        is_installment = data.get('is_installment', False)

        #print(f"DEBUG: source_type recebido no serializer.validate: {source_type} (type: {type(source_type)})")

        if source_type == 'BANK_ACCOUNT':
            if credit_card:
                raise serializers.ValidationError({"credit_card": _("Credit card cannot be set for bank account transactions.")})

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
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False)

    class Meta(TransactionBaseSerializer.Meta):
        fields = [
            'id', 'description', 'amount', 'issue_date',
            'type', 'source_type', 'category', 'status',
            'bank_account', 'credit_card'
        ]

class TransactionDetailSerializer(TransactionBaseSerializer):
    """
    Serializer for retrieving detailed transaction information.
    """
    category_type = serializers.CharField(source='category.type', read_only=True) # PARA OTIMIZAR

    class Meta(TransactionBaseSerializer.Meta):
        fields = TransactionBaseSerializer.Meta.fields + [
            'bank_account', 'credit_card', 'category_type'
        ]
        read_only_fields = TransactionBaseSerializer.Meta.read_only_fields + [
            'bank_account', 'credit_card', 'category_type'
        ]

class TransactionCreateUpdateSerializer(TransactionBaseSerializer):
    """
    Serializer for creating and updating transactions.
    Delegates complex logic to TransactionService.
    """
    apply_to_all_installments = serializers.BooleanField(write_only=True, required=False, default=False)
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False)

    class Meta(TransactionBaseSerializer.Meta):
        fields = [
            'id', 'category', 'description', 'amount', 'issue_date',
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
            'is_installment': {'required': False}
        }
    
    def validate(self, data):
        instance = self.instance

        source_type = data.get('source_type', getattr(instance, 'source_type', None))
        category = data.get('category', getattr(instance, 'category', None))
        is_installment = data.get('is_installment', getattr(instance, 'is_installment', False))
        installment_number = data.get('installment_number', getattr(instance, 'installment_number', None))
        total_installments = data.get('total_installments', getattr(instance, 'total_installments', None))
        credit_card = data.get('credit_card', getattr(instance, 'credit_card', None))
        
        if source_type == 'CREDIT_CARD':
            if category and category.type != 'expense':
                raise serializers.ValidationError({"category": _("Credit card transactions must be of 'expense' category type.")})
            
        if source_type == 'CREDIT_CARD' and credit_card:
            if credit_card.credit_limit < data.get('amount', 0):
                raise serializers.ValidationError({"credit_card": _("Credit card limit is not enough.")})

        if source_type == 'CREDIT_CARD' and is_installment:
            if total_installments is None or total_installments < 1:
                raise serializers.ValidationError({"total_installments": _("Total installments must be a positive number for installment transactions.")})
            if installment_number is None or not (1 <= installment_number <= total_installments):
                raise serializers.ValidationError({"installment_number": _("Installment number must be between 1 and total installments.")})
        elif not is_installment:
            if total_installments is not None or installment_number is not None:
                raise serializers.ValidationError(_("Installment specific fields should be null if not an installment."))
            if source_type == 'CREDIT_CARD' and 'invoice' in data and data['invoice'] is not None:
                 raise serializers.ValidationError({"invoice": _("Invoice should not be directly linked if not an installment transaction (will be linked via installment logic).")})
        
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