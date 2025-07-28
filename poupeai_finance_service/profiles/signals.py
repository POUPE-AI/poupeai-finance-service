import structlog
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict

from .models import Profile
from poupeai_finance_service.core.models import AuditLog

log = structlog.get_logger(__name__)

def get_audit_data_from_context():
    context = structlog.contextvars.get_contextvars()
    return {
        "actor_user_id": context.get("actor_user_id"),
        "source_ip": context.get("source_ip"),
        "correlation_id": context.get("correlation_id"),
    }

@receiver(post_save, sender=Profile)
def audit_profile_changes(sender, instance, created, **kwargs):
    context_data = get_audit_data_from_context()
    
    actor_id = context_data.get("actor_user_id") or instance.user_id

    changes = {}
    action_type = "CREATE" if created else "UPDATE"

    if not created:
        old_values = instance._old_values if hasattr(instance, '_old_values') else {}
        new_values = model_to_dict(instance)
        for field, new_value in new_values.items():
            if field in old_values and old_values[field] != new_value:
                changes[field] = [old_values[field], new_value]
        if not changes:
            return

    AuditLog.objects.create(
        profile_id=instance.pk,
        actor_user_id=actor_id,
        action_type=action_type,
        entity_type='Profile',
        entity_id=str(instance.pk),
        changes=changes if changes else None,
        source_ip=context_data.get("source_ip"),
        correlation_id=context_data.get("correlation_id"),
        service_name=settings.SERVICE_NAME,
    )
    log.info(
        f"Profile audit log created for action: {action_type}",
        event_type=f"PROFILE_{action_type}D",
        actor_user_id=actor_id,
        trigger_type="user_request",
        event_details={"profile_id": str(instance.pk), "changes": changes}
    )

@receiver(post_delete, sender=Profile)
def audit_profile_deletion(sender, instance, **kwargs):
    context_data = get_audit_data_from_context()
    actor_id = context_data.get("actor_user_id")

    AuditLog.objects.create(
        profile_id=instance.pk,
        actor_user_id=actor_id,
        action_type="DELETE",
        entity_type='Profile',
        entity_id=str(instance.pk),
        source_ip=context_data.get("source_ip"),
        correlation_id=context_data.get("correlation_id"),
        service_name=settings.SERVICE_NAME,
    )
    log.info(
        "Profile audit log created for action: DELETE",
        event_type="PROFILE_DELETED",
        actor_user_id=actor_id,
        trigger_type="system_scheduled",
        event_details={"profile_id": str(instance.pk)}
    )