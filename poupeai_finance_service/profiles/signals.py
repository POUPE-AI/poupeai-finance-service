import structlog
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict

from datetime import date, datetime
from uuid import UUID

from .models import Profile
from poupeai_finance_service.core.models import AuditLog
from poupeai_finance_service.core.events import EventType

log = structlog.get_logger(__name__)

def get_audit_data_from_context():
    context = structlog.contextvars.get_contextvars()
    return {
        "actor_user_id": context.get("actor_user_id"),
        "source_ip": context.get("source_ip"),
        "correlation_id": context.get("correlation_id"),
        "user_agent": context.get("user_agent"),
    }

@receiver(post_save, sender=Profile)
def audit_profile_changes(sender, instance, created, **kwargs):
    context_data = get_audit_data_from_context()
    actor_id = context_data.get("actor_user_id")

    changes = {}
    if created:
        action_type = "CREATE"
        event_type = EventType.PROFILE_CREATED
    else:
        action_type = "UPDATE"
        event_type = EventType.PROFILE_UPDATED

    if not created:
        old_values = getattr(instance, '_old_values', {})
        new_values = model_to_dict(instance)
        for field, new_value in new_values.items():
            if field in old_values and str(old_values.get(field)) != str(new_value):
                changes[field] = [old_values.get(field), new_value]
        
        if not changes:
            return

    safe_changes = {}
    for field, values in changes.items():
        safe_values = []
        for value in values:
            if isinstance(value, (datetime, date)):
                safe_values.append(value.isoformat())
            elif isinstance(value, UUID):
                safe_values.append(str(value))
            else:
                safe_values.append(value)
        safe_changes[field] = safe_values

    AuditLog.objects.create(
        profile_id=instance.pk,
        actor_user_id=actor_id,
        action_type=action_type,
        entity_type='Profile',
        entity_id=str(instance.pk),
        changes=safe_changes,
        source_ip=context_data.get("source_ip"),
        user_agent=context_data.get("user_agent"),
        correlation_id=context_data.get("correlation_id"),
        service_name=settings.SERVICE_NAME,
    )
    
    log.info(
        f"Profile audit log created for action: {action_type}",
        event_type=event_type,
        actor_user_id=actor_id,
        trigger_type=context_data.get("trigger_type"),
        event_details={"profile_id": str(instance.pk), "changes": safe_changes}
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
        event_type=EventType.PROFILE_DELETED,
        actor_user_id=actor_id,
        trigger_type="system_scheduled",
        event_details={"profile_id": str(instance.pk)}
    )