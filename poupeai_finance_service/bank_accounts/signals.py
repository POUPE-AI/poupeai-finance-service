from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from .models import BankAccount

@receiver(pre_delete, sender=BankAccount)
def prevent_default_bank_account_deletion(sender, instance, **kwargs):
    if instance.is_default:
        raise ValidationError("Cannot delete a default bank account. Please set another account as default first.")