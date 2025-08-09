import structlog
from poupeai_finance_service.core.events import EventType

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
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
from poupeai_finance_service.profiles.api.permissions import IsProfileActive
from poupeai_finance_service.transactions.models import Transaction
from poupeai_finance_service.transactions.services import TransactionService

log = structlog.get_logger(__name__)

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
    permission_classes = [IsProfileActive, IsAuthenticated, IsOwnerProfile]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['purchase_group_uuid', 'category', 'source_type', 'type']
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
        user_profile = self.request.user
        queryset = self.queryset.filter(profile=user_profile).select_related(
            'category', 'bank_account', 'credit_card'
        )

        issue_date_start = self.request.query_params.get('issue_date_start')
        if issue_date_start:
            queryset = queryset.filter(issue_date__gte=issue_date_start)

        issue_date_end = self.request.query_params.get('issue_date_end')
        if issue_date_end:
            queryset = queryset.filter(issue_date__lte=issue_date_end)
        
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            log.info(
                "Transaction created successfully",
                event_type=EventType.TRANSACTION_CREATED,
                event_details={
                    "transaction_id": serializer.instance.id,
                    "type": serializer.instance.type,
                    "source_type": serializer.instance.source_type,
                    "amount": float(serializer.instance.amount)
                }
            )
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except (DRFValidationError, DjangoValidationError) as e:
            log.warning(
                "Transaction creation failed due to validation error",
                event_type=EventType.TRANSACTION_CREATION_FAILED,
                event_details={"errors": e.detail if hasattr(e, 'detail') else str(e)}
            )
            raise
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            log.info(
                "Transaction updated successfully",
                event_type=EventType.TRANSACTION_UPDATED,
                event_details={
                    "transaction_id": instance.id,
                    "updated_fields": list(serializer.validated_data.keys())
                }
            )

            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}

            return Response(serializer.data)
        except (DRFValidationError, DjangoValidationError) as e:
            log.warning(
                "Transaction update failed due to validation error",
                event_type=EventType.TRANSACTION_UPDATE_FAILED,
                event_details={
                    "transaction_id": instance.id,
                    "errors": e.detail if hasattr(e, 'detail') else str(e)
                }
            )
            raise

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        transaction_id_copy = instance.id
        
        try:
            self.perform_destroy(instance)
            
            log.info(
                "Transaction deleted successfully",
                event_type=EventType.TRANSACTION_DELETED,
                event_details={"transaction_id": transaction_id_copy}
            )

            return Response(status=status.HTTP_204_NO_CONTENT)
        except (DRFValidationError, DjangoValidationError) as e:
            log.warning(
                "Transaction deletion failed",
                event_type=EventType.TRANSACTION_DELETION_FAILED,
                event_details={
                    "transaction_id": transaction_id_copy,
                    "errors": e.detail if hasattr(e, 'detail') else str(e)
                }
            )
            raise

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        deletion_option = self.request.data.get('deletion_option', 'CURRENT_AND_FUTURE')
        TransactionService.delete_transaction(instance, deletion_option)

import time
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from .serializers import PerformanceTestSerializer

class TransactionPerformanceTestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para demonstrar a otimização de queries com N+1 em larga escala.
    Não requer autenticação.
    """
    queryset = Transaction.objects.all()
    serializer_class = PerformanceTestSerializer
    permission_classes = [AllowAny]

    def _get_timed_response(self, queryset):
        start_time = time.perf_counter()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(queryset, many=True)
            response = Response(serializer.data)

        end_time = time.perf_counter()
        processing_time_ms = (end_time - start_time) * 1000

        if isinstance(response.data, dict) and 'results' in response.data:
             response.data['processing_time_ms'] = f"{processing_time_ms:.2f} ms"
        else:
             response.data = {
                 'processing_time_ms': f"{processing_time_ms:.2f} ms",
                 'results': response.data
             }
        
        return response


    @action(detail=False, methods=['get'], url_path='unoptimized')
    def unoptimized_list(self, request, *args, **kwargs):
        """Cenário 1: O problema N+1 clássico (mas paginado)."""
        queryset = Transaction.objects.all()
        return self._get_timed_response(queryset)

    @action(detail=False, methods=['get'], url_path='optimized-join')
    def optimized_join_list(self, request, *args, **kwargs):
        """Cenário 2: A otimização com select_related (JOIN gigante)."""
        queryset = Transaction.objects.select_related(
            'category', 'bank_account', 'credit_card'
        ).all()
        return self._get_timed_response(queryset)

    @action(detail=False, methods=['get'], url_path='optimized-prefetch')
    def optimized_prefetch_list(self, request, *args, **kwargs):
        """Cenário 3: A otimização com prefetch_related."""
        queryset = Transaction.objects.prefetch_related(
            'category', 'bank_account', 'credit_card'
        ).all()
        return self._get_timed_response(queryset)