from django.urls import path, include
from rest_framework.routers import DefaultRouter

from poupeai_finance_service.credit_cards.api.viewsets import CreditCardViewSet, InvoiceViewSet

router = DefaultRouter()
router.register(r'', CreditCardViewSet, basename='credit_cards')

app_name = 'credit_cards'

urlpatterns = [
    path('', include(router.urls)),
    path('<int:id>/invoices/', InvoiceViewSet.as_view({'get': 'list'}), name='invoices_list'),
    path('<int:id>/invoices/<int:pk>/', InvoiceViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='invoices_detail'),
]