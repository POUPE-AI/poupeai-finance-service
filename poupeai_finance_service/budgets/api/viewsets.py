from rest_framework import viewsets
from poupeai_finance_service.budgets.api.serializers import BudgetSerializer, CreateBudgetSerializer
from poupeai_finance_service.budgets.models import Budget
from poupeai_finance_service.profiles.api.permissions import IsProfileActive
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema_view, extend_schema

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
    queryset = Budget.objects.none()
    serializer_class = BudgetSerializer
    permission_classes = [IsProfileActive, IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Budget.objects.filter(profile=user)
        return Budget.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBudgetSerializer
        return BudgetSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['profile'] = self.request.user
        return context