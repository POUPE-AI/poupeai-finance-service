from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from poupeai_finance_service.core.models import TimeStampedModel
from poupeai_finance_service.profiles.models import Profile

class Goal(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)

    color_hex = models.CharField(_('Goal Color'), max_length=7, 
                                 default='#000000', null=False, blank=False)
    
    initial_balance = models.DecimalField(_('Initial Balance'), max_digits=10, 
                                        decimal_places=2, default=0, 
                                        validators=[MinValueValidator(0, 
                                        message='Initial balance cannot be negative')])
    
    goal_amount = models.DecimalField(_('Goal Amount'), max_digits=10, 
                                        decimal_places=2, default=0, 
                                        validators=[MinValueValidator(0, 
                                        message='Goal amount cannot be negative')])
    
    target_at = models.DateField(_('Target At'), null=False, blank=False)
    completed_at = models.DateField(_('Completed At'), null=True, blank=True)
    is_completed = models.BooleanField(_('Is Completed'), default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'profile'],
                name='unique_goal_name_per_profile',
                violation_error_message=_('A goal with this name already exists for this profile')
            )
        ]

        verbose_name = _('Goal')
        verbose_name_plural = _('Goals')
    
    @property
    def current_balance(self):
        return self.initial_balance + sum(deposit.deposit_amount for deposit in self.deposits.all())
    
    @property
    def percentage_completed(self):
        return (self.current_balance / self.goal_amount) * 100
    
    def __str__(self):
        return f'{self.name} - {self.goal_amount}'

class GoalDeposit(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='deposits')

    deposit_amount = models.DecimalField(_('Deposit Amount'), max_digits=10, 
                                        decimal_places=2, default=0, 
                                        validators=[MinValueValidator(0, 
                                        message='Deposit amount cannot be negative')])
    
    deposit_at = models.DateField(_('Deposit At'))
    note = models.TextField(_('Note'), blank=True, null=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Goal Deposit')
        verbose_name_plural = _('Goal Deposits')

    def __str__(self):
        return f'{self.goal.name} - {self.deposit_amount}'
