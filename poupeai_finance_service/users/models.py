from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.utils.translation import gettext_lazy as _

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

class Profile(models.Model):
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

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')
        ordering = ['user__username']

    def __str__(self):
        return f'Profile of {self.user.username}'