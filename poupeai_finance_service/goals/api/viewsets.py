from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from rest_framework import mixins
from poupeai_finance_service.goals.models import Goal
from poupeai_finance_service.goals.api.serializers import (
    GoalCreateSerializer, 
    GoalUpdateSerializer, 
    GoalListSerializer, 
    GoalDetailSerializer, 
    GoalDepositSerializer
)
from poupeai_finance_service.users.api.permissions import IsProfileActive
from poupeai_finance_service.users.querysets import get_profile_by_user
from django.utils import timezone

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
            profile = get_profile_by_user(user)
            return self.queryset.filter(profile=profile)
        return self.queryset.none()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context['profile'] = get_profile_by_user(self.request.user)
        return context
    
class GoalDepositViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = GoalDepositSerializer
    permission_classes = [IsProfileActive, IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context['profile'] = get_profile_by_user(self.request.user)
        
        goal_id = self.kwargs.get('id')
        if goal_id:
            context['goal_id'] = goal_id
            
        return context

    def create(self, request, *args, **kwargs):
        id = self.kwargs.get('id')
        profile = get_profile_by_user(request.user)
        goal = get_object_or_404(Goal, pk=id, profile=profile)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(goal=goal)

        if goal.current_balance >= goal.goal_amount:
            goal.is_completed = True
            goal.completed_at = timezone.now()
            goal.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)