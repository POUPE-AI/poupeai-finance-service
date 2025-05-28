from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from poupeai_finance_service.core.models import TimeStampedModel
from poupeai_finance_service.users.models import Profile
from poupeai_finance_service.credit_cards.validators import validate_day

class CreditCard(TimeStampedModel):
    class BrandChoices(models.TextChoices):
        VISA = "VISA", "Visa"
        MASTERCARD = "MASTERCARD", "Mastercard"
        AMEX = "AMEX", "American Express"
        ELO = "ELO", "Elo"
        HIPERCARD = "HIPERCARD", "Hipercard"

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="credit_cards")

    name = models.CharField(
        max_length=50,
        verbose_name=_("Name")
    )

    credit_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.0, message=_("Credit limit cannot be negative."))],
        verbose_name=_("Credit Limit")
    )

    additional_info = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Additional Info")
    )

    closing_day = models.SmallIntegerField(
        validators=[validate_day],
        verbose_name=_("Closing Day")
    )

    due_day = models.SmallIntegerField(
        validators=[validate_day],
        verbose_name=_("Due Day")
    )

    brand = models.CharField(
        max_length=20,
        choices=BrandChoices.choices,
        verbose_name=_("Brand")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "name"],
                name="unique_credit_card_name_per_profile",
                violation_error_message=_("A credit card with this name already exists for this profile.")
            )
        ]

        verbose_name = _('Credit Card')
        verbose_name_plural = _('Credit Cards')

    def __str__(self):
        """Represents the CreditCard object in a readable form."""
        return f"{self.name} ({self.brand}) - {self.profile.user.get_username() if self.profile.user else self.profile.id}"

    def clean(self):
        super().clean()

        if self.closing_day is not None and self.due_day is not None:
            if self.closing_day == self.due_day:
                raise ValidationError(
                    {'due_day': _("The due day cannot be the same as the closing day.")},
                    code='due_day_equals_closing_day'
                )