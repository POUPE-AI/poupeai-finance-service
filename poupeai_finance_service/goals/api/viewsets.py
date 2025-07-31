import structlog
from poupeai_finance_service.core.events import EventType

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from rest_framework import mixins
from rest_framework.exceptions import ValidationError as DRFValidationError
from drf_spectacular.utils import extend_schema_view, extend_schema
from drf_spectacular.openapi import OpenApiParameter
from poupeai_finance_service.goals.models import Goal
from poupeai_finance_service.goals.api.serializers import (
    GoalCreateSerializer, 
    GoalUpdateSerializer, 
    GoalListSerializer, 
    GoalDetailSerializer, 
    GoalDepositSerializer
)
from poupeai_finance_service.profiles.api.permissions import IsProfileActive
from django.utils import timezone

log = structlog.get_logger(__name__)

@extend_schema_view(
    list=extend_schema(
        tags=['Goals'],
        summary='List all goals',
        description='Retrieve all goals for the authenticated user'
    ),
    create=extend_schema(
        tags=['Goals'],
        summary='Create a new goal',
        description='Create a new financial goal for the authenticated user'
    ),
    retrieve=extend_schema(
        tags=['Goals'],
        summary='Get goal details',
        description='Retrieve detailed information about a specific goal'
    ),
    update=extend_schema(
        tags=['Goals'],
        summary='Update goal',
        description='Update all fields of a specific goal'
    ),
    partial_update=extend_schema(
        tags=['Goals'],
        summary='Partially update goal',
        description='Update specific fields of a goal'
    ),
    destroy=extend_schema(
        tags=['Goals'],
        summary='Delete goal',
        description='Delete a specific goal'
    ),
)
class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all()    
    serializer_class = GoalListSerializer
    permission_classes = [IsProfileActive, IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return GoalCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return GoalUpdateSerializer
        elif self.action == 'retrieve':
            return GoalDetailSerializer
        return GoalListSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            profile = user
            return self.queryset.filter(profile=profile)
        return self.queryset.none()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context['profile'] = self.request.user
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            log.info(
                "Goal created successfully",
                event_type=EventType.GOAL_CREATED,
                event_details={
                    "goal_id": serializer.instance.id,
                    "goal_amount": float(serializer.instance.goal_amount)
                }
            )

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except DRFValidationError as e:
            log.warning(
                "Goal creation failed",
                event_type=EventType.GOAL_CREATION_FAILED,
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
                "Goal updated successfully",
                event_type=EventType.GOAL_UPDATED,
                event_details={
                    "goal_id": instance.id,
                    "updated_fields": list(serializer.validated_data.keys())
                }
            )

            return Response(serializer.data)
        except DRFValidationError as e:
            log.warning(
                "Goal update failed",
                event_type=EventType.GOAL_UPDATE_FAILED,
                event_details={"goal_id": instance.id, "errors": e.detail}
            )
            raise

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        goal_id_copy = instance.id
        try:
            self.perform_destroy(instance)
            log.info(
                "Goal deleted successfully",
                event_type=EventType.GOAL_DELETED,
                event_details={"goal_id": goal_id_copy}
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            log.error(
                "Goal deletion failed unexpectedly",
                event_type=EventType.GOAL_DELETION_FAILED,
                event_details={"goal_id": goal_id_copy},
                exc_info=e
            )
            raise

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user)
    
@extend_schema_view(
    create=extend_schema(
        tags=['Goals Deposits'],
        summary='Add deposit to goal',
        description='Add a deposit to a specific goal',
        parameters=[
            OpenApiParameter(
                name='id',
                description='Goal ID',
                required=True,
                type=int,
                location=OpenApiParameter.PATH
            ),
        ]
    ),
)
class GoalDepositViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = GoalDepositSerializer
    permission_classes = [IsProfileActive, IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context['profile'] = self.request.user
        
        goal_id = self.kwargs.get('id')
        if goal_id:
            context['goal_id'] = goal_id
            
        return context

    def create(self, request, *args, **kwargs):
        goal = get_object_or_404(Goal, pk=self.kwargs.get('id'), profile=request.user)
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            deposit = serializer.save(goal=goal)

            log.info(
                "Deposit made to goal successfully",
                event_type=EventType.GOAL_DEPOSIT_MADE,
                event_details={
                    "goal_id": goal.id,
                    "deposit_id": deposit.id,
                    "deposit_amount": float(deposit.deposit_amount)
                }
            )

            if goal.current_balance >= goal.goal_amount and not goal.is_completed:
                goal.is_completed = True
                goal.completed_at = timezone.now()
                goal.save(update_fields=['is_completed', 'completed_at'])
                
                log.info(
                    "Goal completed",
                    event_type=EventType.GOAL_COMPLETED,
                    event_details={
                        "goal_id": goal.id,
                        "final_balance": float(goal.current_balance)
                    }
                )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except DRFValidationError as e:
            log.warning(
                "Goal deposit failed",
                event_type=EventType.GOAL_DEPOSIT_FAILED,
                event_details={"goal_id": goal.id, "errors": e.detail}
            )
            raise