from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from users.api.views import (
    RegisterUserAPIView, 
    UserProfileAPIView, 
    UserDeactivateAPIView, 
    UserReactivateAPIView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView
)

app_name = "users"

urlpatterns = [
    path('register/', RegisterUserAPIView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('me/profile/', UserProfileAPIView.as_view(), name='user_profile'),
    path('me/delete/', UserDeactivateAPIView.as_view(), name='user_delete'),
    path('me/reactivate/', UserReactivateAPIView.as_view(), name='user_reactivate'),
]