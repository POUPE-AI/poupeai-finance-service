from django.urls import path
from profiles.api.viewsets import ProfileViewSet

app_name = "profiles"

urlpatterns = [
    path('me/', ProfileViewSet.as_view({'get': 'retrieve'}), name='profile-detail'),
    path('me/deactivate/', ProfileViewSet.as_view({'patch': 'deactivate'}), name='profile-deactivate'),
    path('me/reactivate/', ProfileViewSet.as_view({'patch': 'reactivate'}), name='profile-reactivate'),
]