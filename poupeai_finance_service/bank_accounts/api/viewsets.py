from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError

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
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)