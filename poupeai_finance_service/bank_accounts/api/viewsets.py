import structlog
from poupeai_finance_service.core.events import EventType

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema_view, extend_schema

from poupeai_finance_service.bank_accounts.api.serializers import BankAccountSerializer, BankAccountUpdateSerializer
from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.profiles.api.permissions import IsProfileActive

log = structlog.get_logger(__name__)

@extend_schema_view(
    list=extend_schema(
        tags=['Bank Accounts'],
        summary='List bank accounts',
        description='Retrieve all bank accounts for the authenticated user'
    ),
    create=extend_schema(
        tags=['Bank Accounts'],
        summary='Create bank account',
        description='Create a new bank account for the user'
    ),
    retrieve=extend_schema(
        tags=['Bank Accounts'],
        summary='Get bank account',
        description='Retrieve details of a specific bank account'
    ),
    update=extend_schema(
        tags=['Bank Accounts'],
        summary='Update bank account',
        description='Update all fields of a bank account'
    ),
    partial_update=extend_schema(
        tags=['Bank Accounts'],
        summary='Partially update bank account',
        description='Update specific fields of a bank account'
    ),
    destroy=extend_schema(
        tags=['Bank Accounts'],
        summary='Delete bank account',
        description='Delete a specific bank account'
    ),
)
class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    permission_classes = [IsProfileActive, IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user)

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return BankAccountUpdateSerializer
        return BankAccountSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['profile'] = self.request.user
        return context
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            log.info(
                "Bank account created successfully",
                event_type=EventType.BANK_ACCOUNT_CREATED,
                event_details={
                    "bank_account_id": serializer.instance.id,
                    "initial_balance": float(serializer.instance.initial_balance)
                }
            )
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except DRFValidationError as e:
            log.warning(
                "Bank account creation failed",
                event_type=EventType.BANK_ACCOUNT_CREATION_FAILED,
                event_details={"errors": e.detail}
            )
            raise

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            log.info(
                "Bank account updated successfully",
                event_type=EventType.BANK_ACCOUNT_UPDATED,
                event_details={
                    "bank_account_id": instance.id,
                    "updated_fields": list(serializer.validated_data.keys())
                }
            )

            return Response(serializer.data)
        except DRFValidationError as e:
            log.warning(
                "Bank account update failed",
                event_type=EventType.BANK_ACCOUNT_UPDATE_FAILED,
                event_details={"bank_account_id": instance.id, "errors": e.detail}
            )
            raise

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.is_default:
            log.warning(
                "Attempted to delete default bank account",
                event_type=EventType.BANK_ACCOUNT_DELETION_FAILED,
                event_details={
                    "bank_account_id": instance.id,
                    "reason": "Cannot delete a default bank account."
                }
            )
            return Response(
                {'detail': 'Cannot delete a default bank account. Please set another account as default first.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        bank_account_id_copy = instance.id
        try:
            self.perform_destroy(instance)
            log.info(
                "Bank account deleted successfully",
                event_type=EventType.BANK_ACCOUNT_DELETED,
                event_details={"bank_account_id": bank_account_id_copy}
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            log.error(
                "Bank account deletion failed unexpectedly",
                event_type=EventType.BANK_ACCOUNT_DELETION_FAILED,
                event_details={
                    "bank_account_id": bank_account_id_copy,
                    "reason": "This account may have associated transactions."
                    },
                exc_info=e
            )
            return Response(
                {'detail': 'An unexpected error occurred while trying to delete the bank account.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user)