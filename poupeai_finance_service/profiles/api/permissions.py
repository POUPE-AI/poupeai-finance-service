from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone

class IsProfileActive(permissions.BasePermission):
    """
    Custom permission to verify if the user's profile is active.
    Raises a PermissionDenied exception if the profile is deactivated.
    """
    message = 'Your profile is deactivated. Please reactivate it to access this feature.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False 

        profile = request.user
        
        if profile.is_deactivated:
            if profile.deactivation_scheduled_at:
                self.message = (
                    f"Your profile is deactivated and scheduled for permanent deletion on "
                    f"{timezone.localtime(profile.deactivation_scheduled_at).strftime('%Y-%m-%d %H:%M:%S %Z')}. "
                    "Please reactivate it to access this feature."
                )
            raise PermissionDenied(self.message)
            
        return True