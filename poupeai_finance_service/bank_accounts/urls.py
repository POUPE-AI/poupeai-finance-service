from django.urls import path, include
from rest_framework.routers import DefaultRouter
from poupeai_finance_service.bank_accounts.api.viewsets import BankAccountViewSet

router = DefaultRouter()
router.register(r'', BankAccountViewSet, basename='bank-accounts')

app_name = 'bank-accounts'

urlpatterns = [
    path('', include(router.urls)),
]
