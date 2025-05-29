from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.db.models import Sum, F

from poupeai_finance_service.core.models import TimeStampedModel
from poupeai_finance_service.users.models import Profile

class BankAccount(TimeStampedModel):
    name = models.CharField(_('Name'), max_length=50)
    description = models.TextField(_('Description'), blank=True)
    initial_balance = models.DecimalField(
        _('Initial Balance'),
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0, message='Initial balance cannot be negative')]
    )
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='bank_accounts')
    is_default = models.BooleanField(_('Is Default'), default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'profile'],
                name='unique_bank_account_name_per_profile'
            )
        ]

        verbose_name = _('Bank Account')
        verbose_name_plural = _('Bank Accounts')
    
    def save(self, *args, **kwargs):
        if self.is_default:
            BankAccount.objects.filter(profile=self.profile).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Bank Account: {self.name}'
    
    @property
    def current_balance(self):
        """
        Calculates the current balance of the bank account.
        Initial balance + sum of income transactions - sum of expense transactions.
        """
        from poupeai_finance_service.transactions.models import Transaction

        income_transactions = self.transactions.filter(type='income').aggregate(
            total_income=Sum('amount')
        )['total_income'] or 0

        expense_transactions = self.transactions.filter(type='expense').aggregate(
            total_expense=Sum('amount')
        )['total_expense'] or 0
        
        return self.initial_balance + income_transactions - expense_transactions
    