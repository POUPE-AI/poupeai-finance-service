from rest_framework import serializers
from poupeai_finance_service.bank_accounts.models import BankAccount

class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'name', 'description', 'initial_balance', 'is_default', 'created_at', 'updated_at']

class BankAccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'name', 'description', 'is_default']