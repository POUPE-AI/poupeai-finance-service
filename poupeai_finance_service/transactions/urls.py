from django.urls import path, include
from rest_framework.routers import DefaultRouter
from poupeai_finance_service.transactions.api.viewsets import TransactionViewSet, InvoiceViewSet

app_name = 'transactions'

router = DefaultRouter()
router.register(r'', TransactionViewSet, basename='transactions')
router.register(r'invoices', InvoiceViewSet, basename='invoices')

app_name = 'transactions'

urlpatterns = [
    path('', include(router.urls)),
]