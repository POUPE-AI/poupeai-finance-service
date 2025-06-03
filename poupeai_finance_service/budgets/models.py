from django.db import models
from poupeai_finance_service.categories.models import Category
from poupeai_finance_service.users.models import Profile
from poupeai_finance_service.transactions.models import Transaction
from django.utils import timezone

class Budget(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    name = models.CharField(max_length=100, verbose_name="Budget Name")

    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Budget Amount")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    @property
    def actual_amount(self):
        now = timezone.now()
        return self.actual_amount_from_month(now)

    def actual_amount_from_month(self, date):
        total = Transaction.objects.filter(
            category=self.category,
            profile=self.profile,
            transaction_date__year=date.year,
            transaction_date__month=date.month
        ).aggregate(total=models.Sum('amount'))['total'] or 0.0

        return total
    
    class Meta:
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        ordering = ['-created_at']