from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema_view, extend_schema

from poupeai_finance_service.core.permissions import IsOwnerProfile
from poupeai_finance_service.transactions.api.serializers import (
    TransactionCreateUpdateSerializer,
    TransactionDetailSerializer,
    TransactionListSerializer,
)
from poupeai_finance_service.transactions.models import Transaction
from poupeai_finance_service.transactions.services import TransactionService


@extend_schema_view(
    list=extend_schema(
        tags=['Transactions'],
        summary='List all transactions',
        description='Retrieve all transactions for the authenticated user'
    ),
    create=extend_schema(
        tags=['Transactions'],
        summary='Create a new transaction',
        description='Create a new transaction for the authenticated user'
    ),
    retrieve=extend_schema(
        tags=['Transactions'],
        summary='Get a transaction',
        description='Retrieve a specific transaction for the authenticated user'
    ),
    update=extend_schema(
        tags=['Transactions'],
        summary='Update a transaction',
        description='Update a specific transaction for the authenticated user'
    ),
    partial_update=extend_schema(
        tags=['Transactions'],
        summary='Partial update a transaction',
        description='Update a specific transaction for the authenticated user'
    ),
    destroy=extend_schema(
        tags=['Transactions'],
        summary='Delete a transaction',
        description='Delete a specific transaction for the authenticated user'
    ),
)

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerProfile]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['description', 'original_purchase_description', 'original_statement_description']
    ordering_fields = ['issue_date', 'amount', 'created_at']
    ordering = ['-issue_date']

    def get_serializer_class(self):
        if self.action == 'list':
            return TransactionListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TransactionCreateUpdateSerializer
        return TransactionDetailSerializer

    def get_queryset(self):
        user_profile = self.request.user.profile
        queryset = self.queryset.filter(profile=user_profile)

        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        issue_date_start = self.request.query_params.get('issue_date_start')
        if issue_date_start:
            queryset = queryset.filter(issue_date__gte=issue_date_start)

        issue_date_end = self.request.query_params.get('issue_date_end')
        if issue_date_end:
            queryset = queryset.filter(issue_date__lte=issue_date_end)

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
        deletion_option = self.request.data.get('deletion_option')
        try:
            TransactionService.delete_transaction(instance, deletion_option)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DRFValidationError as e:
            raise DRFValidationError(e.detail)
        except Exception as e:
            return Response(
                {"detail": _(f"An error occurred while trying to delete the transaction: {e}")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        try:
            apply_to_all = request.data.get('apply_to_all_installments', False)
            updated_instance = TransactionService.update_transaction(
                instance,
                serializer.validated_data,
                apply_to_all
            )
            return Response(self.get_serializer(updated_instance).data)
        except DjangoValidationError as e:
            if hasattr(e, 'message_dict'):
                raise DRFValidationError(e.message_dict)
            raise DRFValidationError({'detail': str(e)})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deletion_option = request.data.get('deletion_option')
        
        try:
            TransactionService.delete_transaction(instance, deletion_option)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DRFValidationError as e:
            raise DRFValidationError(e.detail)