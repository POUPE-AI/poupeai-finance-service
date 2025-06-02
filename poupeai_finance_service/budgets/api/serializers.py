from rest_framework import serializers
from poupeai_finance_service.budgets.models import Budget

class CreateBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = [
            'category',
            'name',
            'amount'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'actual_amount']
    
    def create(self, validated_data):
        profile = self.context['profile']
        validated_data['profile'] = profile
        return super().create(validated_data)

    def validate(self, attrs):
        if attrs['amount'] <= 0:
            raise serializers.ValidationError("O valor do orçamento deve ser maior que zero.")
        return attrs

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = [
            'id',
            'category',
            'profile',
            'name',
            'amount',
            'actual_amount',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'profile', 'created_at', 'updated_at', 'actual_amount']