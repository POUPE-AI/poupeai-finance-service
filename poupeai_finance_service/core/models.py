from django.db import models
from django.utils.translation import gettext_lazy as _

class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-managed `created_at`
    and `updated_at` fields.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        return f"Object created at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    profile_id = models.UUIDField(_("Profile ID"), help_text=_("The ID of the profile that was targeted by the action (the object of the change)"))
    actor_user_id = models.UUIDField(_("Actor User ID"), null=True, blank=True, help_text=_("The ID of the user who performed the action (the actor). Null if it is a system action."))
    action_time = models.DateTimeField(_("Action Time"), auto_now_add=True)
    action_type = models.CharField(_("Action Type"), max_length=10) # CREATE, UPDATE, DELETE
    entity_type = models.CharField(_("Entity Type"), max_length=100)
    entity_id = models.CharField(_("Entity ID"), max_length=36)
    changes = models.JSONField(_("Changes"), null=True, blank=True)
    source_ip = models.GenericIPAddressField(_("Source IP"), null=True, blank=True)
    user_agent = models.TextField(_("User Agent"), null=True, blank=True)
    correlation_id = models.UUIDField(_("Correlation ID"), null=True, blank=True)
    service_name = models.CharField(_("Service Name"), max_length=50)

    class Meta:
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        ordering = ['-action_time']

    def __str__(self):
        return f"{self.entity_type} {self.action_type} by {self.actor_user_id} at {self.action_time}"