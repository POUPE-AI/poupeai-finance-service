import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from poupeai_finance_service.core.models import TimeStampedModel
from django.forms.models import model_to_dict

class Profile(TimeStampedModel):
    user_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('User ID'),
        help_text=_('Keycloak sub (subject) identifier')
    )
    email = models.EmailField(_('Email'), max_length=255)
    first_name = models.CharField(_('First Name'), max_length=255, blank=True)
    last_name = models.CharField(_('Last Name'), max_length=255, blank=True)
    
    is_deactivated = models.BooleanField(default=False)
    deactivation_scheduled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'profiles'
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')
        ordering = ['email']

    def __str__(self):
        return f'Profile of {self.first_name} {self.last_name}'
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return not self.is_deactivated
    
    @property
    def username(self):
        return self.email
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_values = model_to_dict(self) if self.pk else {}

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._old_values = model_to_dict(self)
    
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