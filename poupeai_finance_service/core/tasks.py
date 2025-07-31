from celery import shared_task
import structlog
from .rabbitmq import rabbitmq_producer

log = structlog.get_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_notification_event_task(self, event_type: str, payload: dict, recipient: dict, correlation_id: str):
    try:
        log.info(
            "Executing publish_notification_event_task",
            event_type=event_type,
            correlation_id=correlation_id,
            attempt=self.request.retries + 1
        )
        rabbitmq_producer.publish(
            event_type=event_type,
            payload=payload,
            recipient=recipient,
            correlation_id=correlation_id
        )
    except Exception as exc:
        log.error(
            "Failed to publish notification event, retrying...",
            event_type=event_type,
            correlation_id=correlation_id,
            exc_info=exc
        )
        raise self.retry(exc=exc)