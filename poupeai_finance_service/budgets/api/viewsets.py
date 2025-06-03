from rest_framework import viewsets
from poupeai_finance_service.budgets.api.serializers import BudgetSerializer, CreateBudgetSerializer
from poupeai_finance_service.budgets.models import Budget
from poupeai_finance_service.users.api.permissions import IsProfileActive
from poupeai_finance_service.users.querysets import get_profile_by_user
from rest_framework.permissions import IsAuthenticated

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.none()
    serializer_class = BudgetSerializer
    permission_classes = [IsProfileActive, IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            profile = get_profile_by_user(self.request.user)
            return Budget.objects.filter(profile=profile)
        return Budget.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBudgetSerializer
        return BudgetSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['profile'] = get_profile_by_user(self.request.user)
        return context