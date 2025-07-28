import structlog
from poupeai_finance_service.core.events import EventType

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from poupeai_finance_service.budgets.api.serializers import BudgetSerializer, CreateBudgetSerializer
from poupeai_finance_service.budgets.models import Budget
from poupeai_finance_service.profiles.api.permissions import IsProfileActive
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema_view, extend_schema

log = structlog.get_logger(__name__)

@extend_schema_view(
    list=extend_schema(
        tags=['Budgets'],
        summary='List all budgets',
        description='Retrieve all budgets for the authenticated user'
    ),
    create=extend_schema(
        tags=['Budgets'],
        summary='Create a new budget',
        description='Create a new budget for the authenticated user'
    ),
    retrieve=extend_schema(
        tags=['Budgets'],
        summary='Get budget details',
        description='Retrieve detailed information about a specific budget'
    ),
    update=extend_schema(
        tags=['Budgets'],
        summary='Update budget',
        description='Update all fields of a specific budget'
    ),
    partial_update=extend_schema(
        tags=['Budgets'],
        summary='Partially update budget',
        description='Update specific fields of a budget'
    ),
    destroy=extend_schema(
        tags=['Budgets'],
        summary='Delete budget',
        description='Delete a specific budget'
    ),
)

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [IsProfileActive, IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBudgetSerializer
        return BudgetSerializer
    
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
                "Budget created successfully",
                event_type=EventType.BUDGET_CREATED,
                event_details={
                    "budget_id": serializer.instance.id,
                    "budget_name": serializer.instance.name,
                    "budget_amount": float(serializer.instance.amount)
                }
            )
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except DRFValidationError as e:
            log.warning(
                "Budget creation failed",
                event_type=EventType.BUDGET_CREATION_FAILED,
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
                "Budget updated successfully",
                event_type=EventType.BUDGET_UPDATED,
                event_details={
                    "budget_id": instance.id,
                    "updated_fields": list(serializer.validated_data.keys())
                }
            )

            return Response(serializer.data)
        except DRFValidationError as e:
            log.warning(
                "Budget update failed",
                event_type=EventType.BUDGET_UPDATE_FAILED,
                event_details={"budget_id": instance.id, "errors": e.detail}
            )
            raise

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        budget_id_copy = instance.id
        try:
            self.perform_destroy(instance)
            log.info(
                "Budget deleted successfully",
                event_type=EventType.BUDGET_DELETED,
                event_details={"budget_id": budget_id_copy}
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            log.error(
                "Budget deletion failed unexpectedly",
                event_type=EventType.BUDGET_DELETION_FAILED,
                event_details={"budget_id": budget_id_copy},
                exc_info=e
            )
            raise