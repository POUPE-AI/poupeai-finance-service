import uuid
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from poupeai_finance_service.core.models import TimeStampedModel
from poupeai_finance_service.users.models import Profile
from poupeai_finance_service.categories.models import Category
from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.credit_cards.models import CreditCard
from .managers import InvoiceManager, TransactionManager

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
    month = models.SmallIntegerField(_('Month'), validators=[MinValueValidator(1), MinValueValidator(12)])
    year = models.SmallIntegerField(_('Year'), validators=[MinValueValidator(2000)])
    amount_paid = models.DecimalField(
        _('Amount Paid'),
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    due_date = models.DateField(_('Due Date'))
    paid = models.BooleanField(_('Paid'), default=False)

    objects = InvoiceManager()

    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        unique_together = ('credit_card', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.credit_card.name} - {self.month}/{self.year}"

    @property
    def total_amount(self):
        """Calculates the total amount of the invoice based on associated credit card transactions."""
        return self.transactions.aggregate(total=models.Sum('amount'))['total'] or 0
    
class Transaction(TimeStampedModel):
    """
    Model representing a financial transaction (income or expense).
    """
    SOURCE_TYPES = (
        ('BANK_ACCOUNT', _('Bank Account')),
        ('CREDIT_CARD', _('Credit Card')),
    )

    TRANSACTION_STATUSES = (
        ('PAID', _('Paid')),
        ('PENDING', _('Pending')),
        ('OVERDUE', _('Overdue')),
        ('CANCELLED', _('Cancelled')),
    )

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('Profile')
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('Category')
    )
    description = models.CharField(_('Description'), max_length=255)
    amount = models.DecimalField(
        _('Amount'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01, message=_("Amount must be positive."))]
    )
    transaction_date = models.DateField(_('Transaction Date'))
    type = models.CharField(
        _('Type'),
        max_length=10,
        choices=Category.CATEGORY_TYPES,
        editable=False
    )
    source_type = models.CharField(
        _('Source Type'),
        max_length=20,
        choices=SOURCE_TYPES
    )

    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='transactions',
        blank=True,
        null=True,
        verbose_name=_('Bank Account')
    )
    credit_card = models.ForeignKey(
        CreditCard,
        on_delete=models.CASCADE,
        related_name='transactions',
        blank=True,
        null=True,
        verbose_name=_('Credit Card')
    )
    is_installment = models.BooleanField(_('Is Installment'), default=False)
    installment_number = models.SmallIntegerField(_('Installment Number'), blank=True, null=True,
                                                  validators=[MinValueValidator(1)])
    total_installments = models.SmallIntegerField(_('Total Installments'), blank=True, null=True,
                                                  validators=[MinValueValidator(1)])
    purchase_group_uuid = models.UUIDField(_('Purchase Group UUID'), default=uuid.uuid4, editable=False, blank=True, null=True)
    original_purchase_description = models.TextField(_('Original Purchase Description'), blank=True, null=True)

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='transactions',
        blank=True,
        null=True,
        verbose_name=_('Invoice')
    )

    original_transaction_id = models.CharField(_('Original Transaction ID'), max_length=100, blank=True, null=True)
    original_statement_description = models.TextField(_('Original Statement Description'), blank=True, null=True)
    attachment = models.CharField(_('Attachment URL'), max_length=255, blank=True, null=True)

    objects = TransactionManager()

    class Meta:
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        ordering = ['-transaction_date', '-created_at']
        
    def __str__(self):
        return f"{self.description} - {self.amount} on {self.transaction_date}"

    def clean(self):
        super().clean()

        if self.source_type == 'BANK_ACCOUNT':
            if not self.bank_account:
                raise ValidationError(_("Bank account is required for bank account transactions."))
            if self.credit_card or self.is_installment or self.installment_number or self.total_installments or self.invoice:
                raise ValidationError(_("Credit card related fields cannot be set for bank account transactions."))
        elif self.source_type == 'CREDIT_CARD':
            if not self.credit_card:
                raise ValidationError(_("Credit card is required for credit card transactions."))
            if self.bank_account:
                raise ValidationError(_("Bank account cannot be set for credit card transactions."))
            
            if self.is_installment:
                if not self.total_installments or self.total_installments < 1:
                    raise ValidationError(_("Total installments must be a positive number for installment transactions."))
                if not self.installment_number or not (1 <= self.installment_number <= self.total_installments):
                    raise ValidationError(_("Installment number must be between 1 and total installments."))
            else:
                if self.total_installments is not None or self.installment_number is not None:
                    raise ValidationError(_("Installment specific fields should be null if not an installment."))
                if self.invoice:
                    raise ValidationError(_("Invoice should not be directly linked if not an installment transaction (will be linked via installment logic)."))

        if self.category and self.type != self.category.type:
            self.type = self.category.type

    @property
    def status(self):
        """
        Returns the status of the transaction.
        For BANK_ACCOUNT: PAID.
        For CREDIT_CARD: PAID, PENDING, OVERDUE.
        """
        if self.source_type == 'BANK_ACCOUNT':
            return 'PAID'
        elif self.source_type == 'CREDIT_CARD' and self.invoice:
            if self.invoice.paid:
                return 'PAID'
            elif self.invoice.due_date < timezone.now().date() and not self.invoice.paid:
                return 'OVERDUE'
            else:
                return 'PENDING'
        return 'PENDING'