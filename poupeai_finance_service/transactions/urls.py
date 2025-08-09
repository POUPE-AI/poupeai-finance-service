from django.urls import path, include
from rest_framework.routers import DefaultRouter

from poupeai_finance_service.transactions.api.viewsets import (
    TransactionViewSet,
    TransactionPerformanceTestViewSet
)

app_name = 'transactions'

router = DefaultRouter()
router.register(r'', TransactionViewSet, basename='transactions')

performance_router = DefaultRouter()
performance_router.register(r'performance-test', TransactionPerformanceTestViewSet, basename='performance-test')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(performance_router.urls)),
]