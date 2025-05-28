from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

def validate_date_not_in_past(value):
    """
    Validates that the date is not in the past.
    """
    if value and value < timezone.now().date():
        raise ValidationError(
            _("The date cannot be in the past."),
            code='date_in_past'
        )