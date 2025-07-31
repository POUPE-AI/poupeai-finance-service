import structlog
from poupeai_finance_service.core.events import EventType

from typing import Any
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from drf_spectacular.utils import extend_schema_view, extend_schema

from poupeai_finance_service.profiles.api.permissions import IsProfileActive

from poupeai_finance_service.categories.api.serializers import CategorySerializer, CreateCategorySerializer
from poupeai_finance_service.categories.models import Category

log = structlog.get_logger(__name__)

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
        context['profile'] = self.request.user
        return context
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return self.queryset.filter(profile=user)
        return self.queryset.none()
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            log.info(
                "Category created successfully",
                event_type=EventType.CATEGORY_CREATED,
                event_details={
                    "category_id": serializer.instance.id,
                    "category_name": serializer.instance.name,
                    "category_type": serializer.instance.type
                }
            )
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except DRFValidationError as e:
            log.warning(
                "Category creation failed",
                event_type=EventType.CATEGORY_CREATION_FAILED,
                event_details={"errors": e.detail}
            )
            raise

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            log.info(
                "Category updated successfully",
                event_type=EventType.CATEGORY_UPDATED,
                event_details={
                    "category_id": instance.id,
                    "updated_fields": list(serializer.validated_data.keys())
                }
            )

            return Response(serializer.data)
        except DRFValidationError as e:
            log.warning(
                "Category update failed",
                event_type=EventType.CATEGORY_UPDATE_FAILED,
                event_details={"category_id": instance.id, "errors": e.detail}
            )
            raise

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        category_id_copy = instance.id
        try:
            self.perform_destroy(instance)
            log.info(
                "Category deleted successfully",
                event_type=EventType.CATEGORY_DELETED,
                event_details={"category_id": category_id_copy}
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            log.error(
                "Category deletion failed unexpectedly",
                event_type=EventType.CATEGORY_DELETION_FAILED,
                event_details={"category_id": category_id_copy},
                exc_info=e
            )
            raise