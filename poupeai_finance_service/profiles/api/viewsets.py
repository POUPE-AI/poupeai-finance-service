import structlog
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from poupeai_finance_service.profiles.models import Profile
from poupeai_finance_service.profiles.api.serializers import ProfileSerializer
from poupeai_finance_service.profiles.api.permissions import IsProfileActive
from poupeai_finance_service.core.events import EventType
from poupeai_finance_service.core.tasks import publish_notification_event_task
from poupeai_finance_service.core.middleware import get_correlation_id

log = structlog.get_logger(__name__)

class ProfileViewSet(viewsets.GenericViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    @extend_schema(
        tags=['User Management'],
        summary='Get user profile',
        description='Retrieve the authenticated user profile information',
        responses={
            200: ProfileSerializer,
            401: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string", "example": "Authentication credentials were not provided."}
                }
            }
        }
    )
    def retrieve(self, request):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['User Management'],
        summary='Deactivate user account',
        description='Deactivate the authenticated user account and schedule for deletion',
        methods=['patch'],
        responses={
            200: {
                "type": "object", 
                "properties": {
                    "detail": {"type": "string", "example": "Profile successfully deactivated. Permanent deletion is scheduled."}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string", "example": "User profile is already deactivated or has scheduled deletion."}
                }
            }
        }
    )
    def deactivate(self, request):
        instance = self.get_object()
        
        if instance.is_deactivated:
            log.warning(
                "Attempted to deactivate an already deactivated profile",
                event_type=EventType.PROFILE_DEACTIVATION_FAILED,
                actor_user_id=request.user.user_id,
                event_details={"reason": "Profile already deactivated."}
            )
            return Response(
                {"detail": "User profile is already deactivated or has scheduled deletion."},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.deactivate(schedule_deletion_in_days=30)

        log.info(
            "User profile deactivated successfully",
            event_type=EventType.PROFILE_DEACTIVATED,
            actor_user_id=request.user.user_id,
            event_details={"scheduled_deletion_at": instance.deactivation_scheduled_at}
        )

        correlation_id = get_correlation_id()
        recipient_data = {
            "user_id": str(instance.user_id),
            "email": instance.email,
            "name": f"{instance.first_name} {instance.last_name}".strip(),
        }
        
        local_deactivation_time = timezone.localtime(instance.deactivation_scheduled_at)
    
        payload_data = {
            "deletion_scheduled_at": local_deactivation_time.isoformat(),
            "reactivate_account_deep_link": "https://poupe.ai/reactivate-account"
        }

        publish_notification_event_task.delay(
            event_type=EventType.PROFILE_DELETION_SCHEDULED,
            payload=payload_data,
            recipient=recipient_data,
            correlation_id=correlation_id
        )

        log.info(
            "Scheduled PROFILE_DELETION_SCHEDULED notification task",
            event_type=EventType.PROFILE_DELETION_SCHEDULED,
            actor_user_id=request.user.user_id,
            correlation_id=correlation_id
        )

        return Response(
            {"detail": "Profile successfully deactivated. Permanent deletion is scheduled."},
            status=status.HTTP_200_OK 
        )
    
    @extend_schema(
        tags=['User Management'],
        summary='Reactivate user account',
        description='Reactivate a previously deactivated user account and cancel scheduled deletion',
        methods=['patch'],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string", "example": "Profile successfully reactivated. Scheduled deletion has been canceled."}
                }
            },
            400: {
                "type": "object", 
                "properties": {
                    "detail": {"type": "string", "example": "User profile is already active."}
                }
            }
        }
    )
    def reactivate(self, request):
        instance = self.get_object()

        if not instance.is_deactivated:
            log.warning(
                "Attempted to reactivate an already active profile",
                event_type=EventType.PROFILE_REACTIVATION_FAILED,
                actor_user_id=request.user.user_id,
                event_details={"reason": "Profile already active."}
            )
            return Response(
                {"detail": "User profile is already active."},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.reactivate()

        log.info(
            "User profile reactivated successfully",
            event_type=EventType.PROFILE_REACTIVATED,
            actor_user_id=request.user.user_id,
        )   
        return Response(
            {"detail": "Profile successfully reactivated. Scheduled deletion has been canceled."},
            status=status.HTTP_200_OK
        ) 