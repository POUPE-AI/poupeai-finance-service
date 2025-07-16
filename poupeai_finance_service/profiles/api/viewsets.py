from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from poupeai_finance_service.profiles.models import Profile
from poupeai_finance_service.profiles.api.serializers import ProfileSerializer
from poupeai_finance_service.profiles.api.permissions import IsProfileActive

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
            return Response(
                {"detail": "User profile is already deactivated or has scheduled deletion."},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.deactivate(schedule_deletion_in_days=30)

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
            return Response(
                {"detail": "User profile is already active."},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.reactivate()

        return Response(
            {"detail": "Profile successfully reactivated. Scheduled deletion has been canceled."},
            status=status.HTTP_200_OK
        ) 