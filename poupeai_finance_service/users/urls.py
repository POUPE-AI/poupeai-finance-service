from django.urls import path, include

urlpatterns = [
    path("api/v1/users/", include("users.api.urls", namespace="users")),
]