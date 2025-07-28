import structlog
from django.conf import settings

def audit_formatter_processor(logger, method_name: str, event_dict: dict) -> dict:
    if 'event_type' not in event_dict:
        return event_dict

    output_dict = {
        "timestamp": event_dict.pop("timestamp"),
        "level": event_dict.pop("level").upper(),
        "service_name": settings.SERVICE_NAME,
        "correlation_id": event_dict.pop("correlation_id", None),
        "trigger_type": event_dict.pop("trigger_type", "system_scheduled"),
        "event_type": event_dict.pop("event_type"),
        "message": event_dict.pop("event"),
    }

    actor_user_id = event_dict.pop("actor_user_id", None)
    if actor_user_id:
        output_dict["actor"] = {
            "user_id": str(actor_user_id),
            "source_ip": event_dict.pop("source_ip", "N/A")
        }
    else:
        output_dict["actor"] = None

    event_dict.pop('_record', None)
    event_dict.pop('_logger', None)
    output_dict["event_details"] = event_dict

    return output_dict