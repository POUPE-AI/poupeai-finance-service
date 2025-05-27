from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from poupeai_finance_service.users.api.permissions import IsProfileActive

from poupeai_finance_service.categories.api.serializers import CategorySerializer
from poupeai_finance_service.categories.models import Category

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsProfileActive, IsAuthenticated]