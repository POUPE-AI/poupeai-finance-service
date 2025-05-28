from django.urls import path, include
from rest_framework.routers import DefaultRouter
from poupeai_finance_service.credit_cards.api.viewsets import CreditCardViewSet

router = DefaultRouter()
router.register(r'', CreditCardViewSet, basename='credit_cards')

app_name = 'credit_cards'

urlpatterns = [
    path('', include(router.urls)),
]