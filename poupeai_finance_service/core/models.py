from django.db import models

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