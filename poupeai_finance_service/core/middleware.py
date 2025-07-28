import time
import uuid
import structlog
from django.conf import settings

log = structlog.get_logger(__name__)

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.monotonic()
        
        structlog.contextvars.clear_contextvars()

        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        source_ip = self.get_client_ip(request)
        
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            source_ip=source_ip,
            user_agent=user_agent,
            trigger_type="user_request",
        )

        response = self.get_response(request)

        actor_user_id = None
        if hasattr(request, "user") and request.user.is_authenticated and hasattr(request.user, "user_id"):
            actor_user_id = request.user.user_id
        
        if actor_user_id:
            structlog.contextvars.bind_contextvars(actor_user_id=actor_user_id)

        duration_ms = (time.monotonic() - start_time) * 1000

        log.info(
            "Request completed successfully",
            event_type="REQUEST_COMPLETED",
            event_details={
                "http": {
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                },
                "duration_ms": round(duration_ms, 2)
            }
        )
        
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip