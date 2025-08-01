import structlog
from poupeai_finance_service.core.events import EventType

from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import extend_schema_view, extend_schema
from django.db import transaction

from poupeai_finance_service.core.permissions import IsOwnerProfile
from poupeai_finance_service.credit_cards.api.serializers import (
    CreditCardSerializer,
    InvoiceSerializer,
    InvoicePaymentSerializer,
)
from poupeai_finance_service.credit_cards.models import CreditCard, Invoice
from poupeai_finance_service.profiles.api.permissions import IsProfileActive

log = structlog.get_logger(__name__)

@extend_schema_view(
    list=extend_schema(
        tags=['Credit Cards'],
        summary='List credit cards',
        description='Retrieve all credit cards for the authenticated user'
    ),
    create=extend_schema(
        tags=['Credit Cards'],
        summary='Create a new credit card',
        description='Create a new credit card for the authenticated user'
    ),
    retrieve=extend_schema(
        tags=['Credit Cards'],
        summary='Get credit card details',
        description='Retrieve detailed information about a specific credit card'
    ),
    update=extend_schema(
        tags=['Credit Cards'],
        summary='Update a credit card',
        description='Update all fields of a specific credit card'
    ),
    partial_update=extend_schema(
        tags=['Credit Cards'],
        summary='Partial update a credit card',
        description='Update specific fields of a credit card'
    ),
    destroy=extend_schema(
        tags=['Credit Cards'],
        summary='Delete a credit card',
        description='Delete a specific credit card for the authenticated user'
    ),
)

class CreditCardViewSet(ModelViewSet):
    queryset = CreditCard.objects.all()
    serializer_class = CreditCardSerializer
    permission_classes = [IsProfileActive, IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            profile = user
            return self.queryset.filter(profile=profile).order_by('name')
        return self.queryset.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context['profile'] = self.request.user
        return context
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            log.info(
                "Credit card created successfully",
                event_type=EventType.CREDIT_CARD_CREATED,
                event_details={"credit_card_id": serializer.instance.id}
            )
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except DRFValidationError as e:
            log.warning(
                "Credit card creation failed",
                event_type=EventType.CREDIT_CARD_CREATION_FAILED,
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
                "Credit card updated successfully",
                event_type=EventType.CREDIT_CARD_UPDATED,
                event_details={"credit_card_id": instance.id}
            )
            return Response(serializer.data)
        except DRFValidationError as e:
            log.warning(
                "Credit card update failed",
                event_type=EventType.CREDIT_CARD_UPDATE_FAILED,
                event_details={"credit_card_id": instance.id, "errors": e.detail}
            )
            raise

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        credit_card_id_copy = instance.id
        try:
            self.perform_destroy(instance)
            log.info(
                "Credit card deleted successfully",
                event_type=EventType.CREDIT_CARD_DELETED,
                event_details={"credit_card_id": credit_card_id_copy}
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            log.error(
                "Credit card deletion failed unexpectedly",
                event_type=EventType.CREDIT_CARD_DELETION_FAILED,
                event_details={"credit_card_id": credit_card_id_copy},
                exc_info=e
            )
            raise
            
    def perform_create(self, serializer):
        serializer.save(profile=self.request.user)

@extend_schema_view(
    list=extend_schema(
        tags=['Invoices'],
        summary='List credit card invoices',
        description='Retrieve all invoices for a specific credit card'
    ),
    retrieve=extend_schema(
        tags=['Invoices'],
        summary='Get invoice details',
        description='Retrieve detailed information about a specific invoice'
    ),
    destroy=extend_schema(
        tags=['Invoices'],
        summary='Delete an invoice',
        description='Delete a specific invoice for the authenticated user'
    ),
    payment=extend_schema(
        tags=['Invoices'],
        summary='Pay an invoice',
        description='Registers the payment for a specific invoice.',
        request=InvoicePaymentSerializer,
        responses={204: None}
    ),
    reopen=extend_schema(
        tags=['Invoices'],
        summary='Reopen a paid invoice',
        description='Reverts a paid invoice back to the open state.',
        request=None,
        responses={204: None}
    ),
)
class InvoiceViewSet(mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsOwnerProfile]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['due_date', 'month', 'year']
    ordering = ['-year', '-month']

    def get_queryset(self):
        user_profile = self.request.user
        credit_card_id = self.kwargs.get('id')

        if not credit_card_id:
            raise NotFound("Credit card ID not provided in the URL.")

        try:
            credit_card = CreditCard.objects.get(pk=credit_card_id, profile=user_profile)
        except CreditCard.DoesNotExist:
            raise NotFound("Credit card not found or you do not have permission to access it.")

        return self.queryset.filter(credit_card=credit_card)

    @action(detail=True, methods=['post'], url_path='payment')
    def payment(self, request, id=None, pk=None):
        invoice = self.get_object()
        if invoice.is_paid:
            return Response({'detail': _('Invoice already paid.')}, status=status.HTTP_409_CONFLICT)

        context = {'profile': request.user, 'invoice': invoice}
        serializer = InvoicePaymentSerializer(data=request.data, context=context)
        
        try:
            serializer.is_valid(raise_exception=True)
            bank_account = serializer.context['bank_account']
            payment_date = serializer.validated_data['payment_date']

            with transaction.atomic():
                invoice.pay(bank_account=bank_account, payment_date=payment_date)
            
            log.info(
                "Invoice paid successfully",
                event_type=EventType.INVOICE_PAID,
                event_details={
                    "invoice_id": invoice.id,
                    "credit_card_id": invoice.credit_card_id,
                    "amount": float(invoice.total_amount),
                    "paid_with_bank_account_id": bank_account.id
                }
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DRFValidationError as e:
            log.warning(
                "Invoice payment failed",
                event_type=EventType.INVOICE_PAYMENT_FAILED,
                event_details={"invoice_id": invoice.id, "errors": e.detail}
            )
            raise

    @action(detail=True, methods=['post'], url_path='reopen')
    def reopen(self, request, id=None, pk=None):
        invoice = self.get_object()
        if not invoice.is_paid:
            return Response({'detail': _('Invoice is not paid.')}, status=status.HTTP_409_CONFLICT)
        
        try:
            with transaction.atomic():
                invoice.reopen()
            
            log.info(
                "Invoice reopened successfully",
                event_type=EventType.INVOICE_REOPENED,
                event_details={"invoice_id": invoice.id}
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            log.error(
                "Invoice reopen failed unexpectedly",
                event_type=EventType.INVOICE_REOPEN_FAILED,
                event_details={"invoice_id": invoice.id},
                exc_info=e
            )
            raise

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        invoice_id_copy = instance.id
        try:
            instance.delete()
            log.info(
                "Invoice deleted successfully",
                event_type=EventType.INVOICE_DELETED,
                event_details={"invoice_id": invoice_id_copy}
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            log.error(
                "Error deleting invoice",
                event_type=EventType.INVOICE_DELETION_FAILED,
                event_details={"invoice_id": invoice_id_copy, "error": str(e)},
                exc_info=e
            )
            return Response(
                {"detail": _(f"Error deleting invoice: {str(e)}")},
                status=status.HTTP_400_BAD_REQUEST
            )