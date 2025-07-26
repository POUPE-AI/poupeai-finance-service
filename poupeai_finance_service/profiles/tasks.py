from celery import shared_task
from django.utils import timezone
from .models import Profile
from poupeai_finance_service.core.keycloak import delete_keycloak_user
import logging

logger = logging.getLogger(__name__)

@shared_task
def remove_expired_profiles():
    now = timezone.now()
    expired_profiles = Profile.objects.filter(
        deactivation_scheduled_at__isnull=False,
        deactivation_scheduled_at__lte=now,
    )

    if not expired_profiles.exists():
        logger.info("No expired profiles to remove.")
        return "No expired profiles to remove."

    deleted_count = 0
    failed_ids = []

    for profile in expired_profiles:
        logger.info(f"Processing profile for user_id: {profile.user_id}")
        
        keycloak_deletion_successful = delete_keycloak_user(user_id=str(profile.user_id))

        if keycloak_deletion_successful:
            try:
                profile.delete()
                deleted_count += 1
                logger.info(f"Successfully deleted local profile for user_id: {profile.user_id}")
            except Exception as e:
                logger.error(f"Failed to delete local profile for user_id {profile.user_id} after Keycloak deletion: {e}")
                failed_ids.append(profile.user_id)
        else:
            logger.error(f"Failed to delete user {profile.user_id} in Keycloak. Skipping local profile deletion.")
            failed_ids.append(profile.user_id)
            
    summary = f"Removed {deleted_count} expired profiles."
    if failed_ids:
        summary += f" Failed to remove profiles for user_ids: {failed_ids}."
        
    logger.info(summary)
    return summary