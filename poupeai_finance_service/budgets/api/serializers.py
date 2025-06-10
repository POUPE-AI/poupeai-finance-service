from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
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
    
    def validate_category(self, category):
        profile = self.context.get('profile')
        if category and profile and category.profile != profile:
            raise serializers.ValidationError(_("Category does not belong to your profile."))
        return category

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
    
    def validate_category(self, category):
        profile = self.context.get('profile') or (self.instance and self.instance.profile)
        if category and profile and category.profile != profile:
            raise serializers.ValidationError(_("Category does not belong to your profile."))
        return category