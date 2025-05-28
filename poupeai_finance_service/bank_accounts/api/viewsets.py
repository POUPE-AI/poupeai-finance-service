from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from poupeai_finance_service.bank_accounts.api.serializers import BankAccountSerializer, BankAccountUpdateSerializer
from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.users.api.permissions import IsProfileActive

class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    permission_classes = [IsProfileActive, IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user.profile)

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return BankAccountUpdateSerializer
        return BankAccountSerializer

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)