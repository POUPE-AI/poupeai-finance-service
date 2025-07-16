from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from poupeai_finance_service.core.models import TimeStampedModel
from poupeai_finance_service.profiles.models import Profile
from poupeai_finance_service.bank_accounts.models import BankAccount
from .managers import InvoiceManager
from .validators import validate_day, validate_closing_due_days_not_equal

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
        return f"{self.name} ({self.brand}) - {self.profile.user.get_username() if self.profile.user else self.profile.id}"

    def clean(self):
        super().clean()

        try:
            validate_closing_due_days_not_equal(self.closing_day, self.due_day)
        except ValidationError as e:
            raise ValidationError({'due_day': e.message})

class Invoice(TimeStampedModel):
    """
    Model representing a credit card invoice.
    """
    credit_card = models.ForeignKey(
        CreditCard,
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name=_('Credit Card')
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        related_name="paid_invoices",
        null=True,
        blank=True,
        verbose_name=_('Bank Account')
    )
    month = models.SmallIntegerField(_('Month'), validators=[MinValueValidator(1), MinValueValidator(12)])
    year = models.SmallIntegerField(_('Year'), validators=[MinValueValidator(2000)])
    due_date = models.DateField(_('Due Date'))
    payment_date = models.DateField(_('Payment Date'), null=True, blank=True)

    objects = InvoiceManager()

    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        unique_together = ('credit_card', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.credit_card.name} - {self.month}/{self.year}"

    @property
    def is_paid(self):
        return self.payment_date is not None

    @property
    def total_amount(self):
        """Calculates the total amount of the invoice based on associated credit card transactions."""
        return self.transactions.aggregate(total=models.Sum('amount'))['total'] or 0
    
    def delete(self, *args, **kwargs):
        from poupeai_finance_service.transactions.models import Transaction
        
        with transaction.atomic():
            related_transactions = self.transactions.all()
            
            installment_groups = {}
            for trans in related_transactions:
                if trans.is_installment and trans.purchase_group_uuid:
                    group_uuid = trans.purchase_group_uuid
                    if group_uuid not in installment_groups:
                        installment_groups[group_uuid] = []
                    installment_groups[group_uuid].append(trans)
            
            non_installment_trans = related_transactions.filter(is_installment=False)
            non_installment_trans.delete()
            
            for group_uuid, transactions in installment_groups.items():
                transactions_ids = [t.id for t in transactions]
                Transaction.objects.filter(id__in=transactions_ids).delete()
                
                remaining_installments = Transaction.objects.filter(
                    purchase_group_uuid=group_uuid
                ).order_by('installment_number')
                
                if remaining_installments.exists():
                    for idx, trans in enumerate(remaining_installments, start=1):
                        trans.installment_number = idx
                        original_desc = trans.original_purchase_description or trans.description.split(' (')[0]
                        trans.description = f"{original_desc} ({idx}/{remaining_installments.count()})"
                        trans.save()
                    
                    remaining_installments.update(total_installments=remaining_installments.count())
            
            super().delete(*args, **kwargs)