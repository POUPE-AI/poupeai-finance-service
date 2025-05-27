from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from poupeai_finance_service.core.models import TimeStampedModel

class CustomUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    """
    groups = models.ManyToManyField(
        Group,
        related_name="customuser_set",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )

    class Meta:
        app_label = 'users'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['username']

    pass

class Profile(TimeStampedModel):
    """
    User profile model to store additional data.
    One-to-one relationship with CustomUser.
    """
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
        ('O', _('Other')),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    gender = models.CharField(_('Gender'), max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(_('Date of Birth'), blank=True, null=True)

    is_deactivated = models.BooleanField(default=False)
    deactivation_scheduled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')
        ordering = ['user__username']

    def __str__(self):
        return f'Profile of {self.user.username}'
    
    def deactivate(self, schedule_deletion_in_days=30):
        """
        Deactivates the profile and schedules a permanent deletion.
        """
        self.is_deactivated = True
        self.deactivation_scheduled_at = timezone.now() + timezone.timedelta(days=schedule_deletion_in_days)
        self.save()

    def reactivate(self):
        """
        Reactivates the profile, canceling any scheduled deletion.
        """
        self.is_deactivated = False
        self.deactivation_scheduled_at = None
        self.save()