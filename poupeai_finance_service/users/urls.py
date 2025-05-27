from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from users.api.views import RegisterUserAPIView, UserProfileAPIView

app_name = "users"

urlpatterns = [
    path('register/', RegisterUserAPIView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', UserProfileAPIView.as_view(), name='user_profile'),
]