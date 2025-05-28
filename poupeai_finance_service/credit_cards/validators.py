from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_day(value):
    """
    Validates if the given value is a valid day (between 1 and 31).

    Args:
        value (int): The value to be validated.

    Raises:
        ValidationError: If the value is not between 1 and 31.
    """
    if not (1 <= value <= 31):
        raise ValidationError(
            _("%(value)s is not a valid day. Please enter a number between 1 and 31."),
            params={"value": value}
        )