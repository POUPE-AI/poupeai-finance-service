import uuid
import structlog
from celery import shared_task
from django.utils import timezone
from .models import Profile
from poupeai_finance_service.core.keycloak import delete_keycloak_user
from poupeai_finance_service.core.events import EventType

log = structlog.get_logger(__name__)

@shared_task
def remove_expired_profiles():
    job_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(
        correlation_id=job_id,
        trigger_type="system_scheduled",
    )

    now = timezone.now()
    expired_profiles = Profile.objects.filter(
        deactivation_scheduled_at__isnull=False,
        deactivation_scheduled_at__lte=now,
    )

    if not expired_profiles.exists():
        log.info("No expired profiles to remove.", event_type=EventType.EXPIRED_PROFILES_CLEANUP_SKIPPED)
        return "No expired profiles to remove."

    deleted_count = 0
    failed_ids = []

    for profile in expired_profiles:
        profile_id_str = str(profile.user_id)
        log.info(f"Processing profile for user_id: {profile_id_str}", event_type=EventType.PROFILE_DELETION_STARTED, event_details={"profile_id": profile_id_str})
        
        keycloak_deletion_successful = delete_keycloak_user(user_id=str(profile.user_id))

        if keycloak_deletion_successful:
            try:
                profile.delete()
                deleted_count += 1
                log.info(f"Successfully deleted profile {profile_id_str}", event_type=EventType.PROFILE_DELETION_SUCCESSFUL, event_details={"profile_id": profile_id_str})
            except Exception as e:
                log.error(f"Failed to delete local profile {profile_id_str}", event_type=EventType.PROFILE_DELETION_FAILED, exc_info=e, event_details={"profile_id": profile_id_str})
                failed_ids.append(profile.user_id)
        else:
            log.error(f"Failed to delete user {profile_id_str} in Keycloak.", event_type=EventType.KEYCLOAK_USER_DELETION_FAILED, event_details={"profile_id": profile_id_str})
            failed_ids.append(profile.user_id)
            
    summary = f"Removed {deleted_count} expired profiles."
    if failed_ids:
        summary += f" Failed to remove profiles for user_ids: {failed_ids}."
        
    log.info(summary, event_type=EventType.EXPIRED_PROFILES_CLEANUP_COMPLETED, event_details={"deleted_count": deleted_count, "failed_count": len(failed_ids)})
    
    structlog.contextvars.clear_contextvars()
    return summary