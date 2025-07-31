from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.utils.translation import gettext_lazy as _
from poupeai_finance_service.bank_accounts.models import BankAccount

class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'name', 'description', 'initial_balance', 'is_default', 'current_balance', 'created_at', 'updated_at']
    
    def validate_name(self, name):
        profile = self.context['profile']
        if BankAccount.objects.filter(profile=profile, name=name).exists():
            raise DRFValidationError(_("A bank account with this name already exists for this profile."))
        return name

class BankAccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'name', 'description', 'is_default']
    
    def validate_name(self, name):
        profile = self.context['profile']
        qs = BankAccount.objects.filter(profile=profile, name=name)
        
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise DRFValidationError(_("A bank account with this name already exists for this profile."))
        return name