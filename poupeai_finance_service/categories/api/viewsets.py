from typing import Any
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema_view, extend_schema

from poupeai_finance_service.users.api.permissions import IsProfileActive
from poupeai_finance_service.users.querysets import get_profile_by_user

from poupeai_finance_service.categories.api.serializers import CategorySerializer, CreateCategorySerializer
from poupeai_finance_service.categories.models import Category

@extend_schema_view(
    list=extend_schema(
        tags=['Categories'],
        summary='List categories',
        description='Get all categories for the authenticated user'
    ),
    create=extend_schema(
        tags=['Categories'],
        summary='Create category',
        description='Create a new transaction category'
    ),
    retrieve=extend_schema(
        tags=['Categories'],
        summary='Get category',
        description='Retrieve details of a specific category'
    ),
    update=extend_schema(
        tags=['Categories'],
        summary='Update category',
        description='Update all fields of a category'
    ),
    partial_update=extend_schema(
        tags=['Categories'],
        summary='Partially update category',
        description='Update specific fields of a category'
    ),
    destroy=extend_schema(
        tags=['Categories'],
        summary='Delete category',
        description='Delete a specific category'
    ),
)
class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    permission_classes = [IsProfileActive, IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateCategorySerializer
        return CategorySerializer
    
    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        context['profile'] = get_profile_by_user(self.request.user)
        return context
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            profile = get_profile_by_user(self.request.user)
            return self.queryset.filter(profile=profile)
        return self.queryset.none()