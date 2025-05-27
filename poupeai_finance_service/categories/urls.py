from django.urls import path, include

from rest_framework.routers import DefaultRouter
from poupeai_finance_service.categories.api.views import CategoryViewSet

router = DefaultRouter()
router.register(r'', CategoryViewSet, basename='category')

app_name = 'categories'

urlpatterns = [
    path('', include(router.urls)), 
]