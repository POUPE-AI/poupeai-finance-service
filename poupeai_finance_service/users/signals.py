from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from poupeai_finance_service.users.models import CustomUser, Profile
from poupeai_finance_service.bank_accounts.models import BankAccount

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile = Profile.objects.create(user=instance)

        BankAccount.objects.create(
            profile=profile,
            name=_('Minha Carteira'),
            is_default=True
        )