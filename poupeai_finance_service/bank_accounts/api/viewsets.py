from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema_view, extend_schema

from poupeai_finance_service.bank_accounts.api.serializers import BankAccountSerializer, BankAccountUpdateSerializer
from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.users.api.permissions import IsProfileActive

@extend_schema_view(
    list=extend_schema(
        tags=['Bank Accounts'],
        summary='List bank accounts',
        description='Retrieve all bank accounts for the authenticated user'
    ),
    create=extend_schema(
        tags=['Bank Accounts'],
        summary='Create bank account',
        description='Create a new bank account for the user'
    ),
    retrieve=extend_schema(
        tags=['Bank Accounts'],
        summary='Get bank account',
        description='Retrieve details of a specific bank account'
    ),
    update=extend_schema(
        tags=['Bank Accounts'],
        summary='Update bank account',
        description='Update all fields of a bank account'
    ),
    partial_update=extend_schema(
        tags=['Bank Accounts'],
        summary='Partially update bank account',
        description='Update specific fields of a bank account'
    ),
    destroy=extend_schema(
        tags=['Bank Accounts'],
        summary='Delete bank account',
        description='Delete a specific bank account'
    ),
)
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