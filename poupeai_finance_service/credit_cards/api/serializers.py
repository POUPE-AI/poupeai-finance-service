from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError
from poupeai_finance_service.credit_cards.models import CreditCard
from poupeai_finance_service.credit_cards.validators import validate_closing_due_days_not_equal
from poupeai_finance_service.users.models import Profile

class CreditCardSerializer(serializers.ModelSerializer):
    brand_display = serializers.CharField(source='get_brand_display', read_only=True)

    class Meta:
        model = CreditCard
        fields = [
            'id',
            'profile',
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
        read_only_fields = ['id', 'profile', 'created_at', 'updated_at', 'brand_display']

    def validate(self, data):
        closing_day = data.get('closing_day', self.instance.closing_day if self.instance else None)
        due_day = data.get('due_day', self.instance.due_day if self.instance else None)

        try:
            validate_closing_due_days_not_equal(closing_day, due_day)
        except ValidationError as e:
            if isinstance(e.message, dict):
                raise DRFValidationError(e.message)
            else:
                raise DRFValidationError({'due_day': e.message})

        return data

    def create(self, validated_data):
        profile = self.context.get('profile')

        if not isinstance(profile, Profile):
            raise DRFValidationError({'profile': _("Profile context not provided correctly for creation.")})

        validated_data['profile'] = profile
        return super().create(validated_data)