from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from poupeai_finance_service.users.models import CustomUser, Profile
from poupeai_finance_service.users.api.serializers import RegisterUserSerializer, UserProfileSerializer
from poupeai_finance_service.users.api.permissions import IsProfileActive

class RegisterUserAPIView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterUserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "User registered successfully. Please login to get your token."
        }, status=status.HTTP_201_CREATED, headers=headers)

class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfileActive]

    def get_object(self):
        return self.request.user.profile
    
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def put(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
    
class UserDeactivateAPIView(generics.DestroyAPIView):
    queryset = Profile.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile
    
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if instance.is_deactivated:
            return Response(
                {"detail": "User profile is already deactivated or has scheduled deletion."},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.deactivate(schedule_deletion_in_days=30)

        return Response(
            {"detail": "Profile successfully deactivated. Permanent deletion is scheduled."},
            status=status.HTTP_200_OK 
        )

class UserReactivateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_profile = request.user.profile

        if not user_profile.is_deactivated:
            return Response(
                {"detail": "User profile is already active."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_profile.reactivate()

        return Response(
            {"detail": "Profile successfully reactivated. Scheduled deletion has been canceled."},
            status=status.HTTP_200_OK
        )