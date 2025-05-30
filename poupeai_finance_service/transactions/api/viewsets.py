from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.utils import timezone

from poupeai_finance_service.transactions.models import Transaction, Invoice
from poupeai_finance_service.transactions.api.serializers import (
    TransactionListSerializer,
    TransactionDetailSerializer,
    TransactionCreateUpdateSerializer,
    InvoiceSerializer
)
from poupeai_finance_service.core.permissions import IsOwnerProfile

class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing financial transactions.
    Provides create, retrieve, update, partial_update, list, and destroy actions.
    """
    queryset = Transaction.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerProfile]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['description', 'original_purchase_description', 'original_statement_description']
    ordering_fields = ['transaction_date', 'amount', 'created_at']
    ordering = ['-transaction_date']

    def get_serializer_class(self):
        if self.action == 'list':
            return TransactionListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TransactionCreateUpdateSerializer
        return TransactionDetailSerializer

    def get_queryset(self):
        """
        Ensures a user can only see their own transactions.
        Applies filtering based on query parameters.
        """
        user_profile = self.request.user.profile
        queryset = self.queryset.filter(profile=user_profile)

        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        transaction_date_start = self.request.query_params.get('transaction_date_start')
        if transaction_date_start:
            queryset = queryset.filter(transaction_date__gte=transaction_date_start)

        transaction_date_end = self.request.query_params.get('transaction_date_end')
        if transaction_date_end:
            queryset = queryset.filter(transaction_date__lte=transaction_date_end)

        source_type = self.request.query_params.get('source_type')
        if source_type:
            queryset = queryset.filter(source_type__iexact=source_type)

        transaction_type = self.request.query_params.get('type') # INCOME or EXPENSE
        if transaction_type:
            queryset = queryset.filter(type__iexact=transaction_type)
        
        status_param = self.request.query_params.get('status')
        if status_param:
            if status_param.upper() == 'PAID':
                queryset = queryset.filter(
                    models.Q(source_type='BANK_ACCOUNT') | 
                    models.Q(source_type='CREDIT_CARD', invoice__paid=True)
                )
            elif status_param.upper() == 'PENDING':
                queryset = queryset.filter(
                    source_type='CREDIT_CARD', 
                    invoice__paid=False, 
                    invoice__due_date__gte=timezone.now().date()
                )
            elif status_param.upper() == 'OVERDUE':
                queryset = queryset.filter(
                    source_type='CREDIT_CARD', 
                    invoice__paid=False, 
                    invoice__due_date__lt=timezone.now().date()
                )

        return queryset
    
    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)
    
    def perform_destroy(self, instance):
        if instance.source_type == 'CREDIT_CARD' and instance.is_installment:
            deletion_option = self.request.data.get('deletion_option')

            if deletion_option == 'CURRENT_ONLY':
                with db_transaction.atomic():
                    instance.delete()
                    remaining_installments = Transaction.objects.filter(
                        purchase_group_uuid=instance.purchase_group_uuid,
                        installment_number__gt=instance.installment_number
                    ).order_by('installment_number')

                    for i, trans in enumerate(remaining_installments):
                        trans.installment_number = instance.installment_number + i
                        trans.save(update_fields=['installment_number', 'updated_at'])
                return Response(status=status.HTTP_204_NO_CONTENT)
            elif deletion_option == 'CURRENT_AND_FUTURE':
                with db_transaction.atomic():
                    Transaction.objects.filter(
                        purchase_group_uuid=instance.purchase_group_uuid,
                        installment_number__gte=instance.installment_number
                    ).delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"detail": _("For installment transactions, 'deletion_option' must be 'CURRENT_ONLY' or 'CURRENT_AND_FUTURE'.")},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class InvoiceViewSet(mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    """
    ViewSet for retrieving and listing Invoices.
    Invoices are primarily generated by the system for credit card transactions.
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsOwnerProfile]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['due_date', 'month', 'year', 'amount_paid']
    ordering = ['-year', '-month']

    def get_queryset(self):
        """
        Ensures a user can only see invoices related to their credit cards.
        """
        user_profile = self.request.user.profile
        return self.queryset.filter(credit_card__profile=user_profile)