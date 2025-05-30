from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from poupeai_finance_service.credit_cards.models import CreditCard, Invoice
from poupeai_finance_service.credit_cards.validators import validate_closing_due_days_not_equal
from poupeai_finance_service.users.models import Profile

class CreditCardSerializer(serializers.ModelSerializer):
    brand_display = serializers.CharField(source='get_brand_display', read_only=True)

    class Meta:
        model = CreditCard
        fields = [
            'id',
            'name',
            'credit_limit',
            'additional_info',
            'closing_day',
            'due_day',
            'brand',
            'brand_display',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'brand_display']

    def validate(self, data):
        profile = self.context.get('profile', self.instance.profile if self.instance else None)
        
        if profile:
            data['profile'] = profile

        self._validate_closing_and_due_days(data)
        self._validate_unique_name_per_profile(data)
        return data

    def _validate_closing_and_due_days(self, data):
        closing_day = data.get('closing_day')
        due_day = data.get('due_day')

        if self.instance:
            if closing_day is None:
                closing_day = self.instance.closing_day
            if due_day is None:
                due_day = self.instance.due_day

        if closing_day is not None and due_day is not None:
            try:
                validate_closing_due_days_not_equal(closing_day, due_day)
            except ValidationError as e:
                raise DRFValidationError({'due_day': e.message_dict if hasattr(e, 'message_dict') else str(e)})
    
    def _validate_unique_name_per_profile(self, data):
        name = data.get('name', self.instance.name if self.instance else None)
        profile = data.get('profile') 

        if not (name and profile):
            return

        qs = CreditCard.objects.filter(profile=profile, name=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise DRFValidationError({"name": _("A credit card with this name already exists for this profile.")})

    def create(self, validated_data):
        profile = validated_data.get('profile')
        if not isinstance(profile, Profile):
             raise DRFValidationError({'profile': _("Profile context not provided correctly for creation.")})

        return super().create(validated_data)

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