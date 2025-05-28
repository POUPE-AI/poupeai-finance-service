from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_day(value):
    """
    Validates if the given value is a valid day (between 1 and 31).
    """
    if not (1 <= value <= 31):
        raise ValidationError(
            _("%(value)s is not a valid day. Please enter a number between 1 and 31."),
            params={"value": value}
        )

def validate_closing_due_days_not_equal(closing_day_value, due_day_value):
    """
    Validates that the closing day and the due date are not the same.
    """
    if closing_day_value is not None and due_day_value is not None:
        if closing_day_value == due_day_value:
            raise ValidationError(
                _("The due day cannot be the same as the closing day."),
                code='due_day_equals_closing_day'
            )