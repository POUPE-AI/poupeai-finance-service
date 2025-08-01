from django.urls import path, include

from rest_framework.routers import DefaultRouter
from poupeai_finance_service.dashboard.api.viewsets import DashboardView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]