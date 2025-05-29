from django.urls import path, include
from rest_framework.routers import DefaultRouter
from poupeai_finance_service.goals.api.viewsets import GoalViewSet, GoalDepositViewSet

router = DefaultRouter()
router.register(r'', GoalViewSet, basename='goals')

app_name = 'goals'

urlpatterns = [
    path('', include(router.urls)),
    path('<int:id>/deposits/', GoalDepositViewSet.as_view({'post': 'create'}), name='goal_deposits'),
]