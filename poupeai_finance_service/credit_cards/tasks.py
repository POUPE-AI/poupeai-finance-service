import uuid
import structlog
from celery import shared_task
from django.utils import timezone

from .models import Invoice
from poupeai_finance_service.core.events import EventType
from poupeai_finance_service.core.tasks import publish_notification_event_task

log = structlog.get_logger(__name__)

@shared_task
def check_and_notify_overdue_invoices():
    today = timezone.localdate()
    correlation_id = str(uuid.uuid4())
    log.info(
        "Starting overdue invoices check",
        trigger_type="system_scheduled",
        correlation_id=correlation_id
    )

    overdue_invoices = Invoice.objects.filter(
        due_date__lt=today,
        payment_date__isnull=True,
        overdue_notification_sent=False
    ).select_related('credit_card__profile')

    if not overdue_invoices.exists():
        log.info("No new overdue invoices found.")
        return "No new overdue invoices found."

    notification_count = 0
    for invoice in overdue_invoices:
        profile = invoice.credit_card.profile
        days_overdue = (today - invoice.due_date).days

        recipient_data = {
            "user_id": str(profile.user_id),
            "email": profile.email,
            "name": f"{profile.first_name} {profile.last_name}".strip(),
        }

        payload_data = {
            "credit_card": invoice.credit_card.name,
            "month": invoice.month,
            "year": invoice.year,
            "due_date": invoice.due_date.isoformat(),
            "amount": float(invoice.total_amount),
            "days_overdue": days_overdue,
            "invoice_deep_link": f"https://poupe.ai/invoices/{invoice.id}"
        }

        publish_notification_event_task.delay(
            event_type=EventType.INVOICE_OVERDUE,
            payload=payload_data,
            recipient=recipient_data,
            correlation_id=correlation_id
        )

        invoice.overdue_notification_sent = True
        invoice.save(update_fields=['overdue_notification_sent'])
        notification_count += 1

        log.info(
            "Overdue invoice notification task scheduled",
            invoice_id=invoice.id,
            user_id=str(profile.user_id),
            correlation_id=correlation_id
        )

    summary = f"Successfully scheduled {notification_count} overdue invoice notifications."
    log.info(summary)
    return summary