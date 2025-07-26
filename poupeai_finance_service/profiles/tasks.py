from celery import shared_task
from django.utils import timezone
from poupeai_finance_service.profiles.models import Profile

@shared_task
def remove_expired_profiles():
    now = timezone.now()
    expired_profiles = Profile.objects.filter(
        deactivation_scheduled_at__isnull=False,
        deactivation_scheduled_at__lte=now,
    )
    count = expired_profiles.count()
    expired_profiles.delete()
    return f'Removed {count} expired profiles.'