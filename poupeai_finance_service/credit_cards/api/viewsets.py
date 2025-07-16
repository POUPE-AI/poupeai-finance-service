from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
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
    permission_classes = [IsAuthenticated, IsProfileActive]

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

        context = {
            'profile': request.user,
            'invoice': invoice
        }
        serializer = InvoicePaymentSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)

        bank_account = serializer.context['bank_account']
        payment_date = serializer.validated_data['payment_date']

        with transaction.atomic():
            invoice.bank_account = bank_account
            invoice.payment_date = payment_date
            invoice.save()

            invoice.transactions.update(
                bank_account=bank_account,
                payment_date=payment_date
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='reopen')
    def reopen(self, request, id=None, pk=None):
        invoice = self.get_object()
        if not invoice.is_paid:
            return Response({'detail': _('Invoice is not paid.')}, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            invoice.bank_account = None
            invoice.payment_date = None
            invoice.save()

            invoice.transactions.update(
                bank_account=None,
                payment_date=None
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        try:
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"detail": _(f"Error deleting invoice: {str(e)}")},
                status=status.HTTP_400_BAD_REQUEST
            )