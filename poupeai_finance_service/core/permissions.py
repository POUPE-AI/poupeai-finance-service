from rest_framework import permissions

class IsOwnerProfile(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object (via profile) to edit or view it.
    Assumes the object has a 'profile' ForeignKey.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True


        if hasattr(obj, 'profile'):
            return obj.profile == request.user.profile
        
        if hasattr(obj, 'user') and hasattr(request.user, 'profile'):
            return obj == request.user.profile

        if hasattr(obj, 'credit_card') and hasattr(request.user, 'profile'):
            return obj.credit_card.profile == request.user.profile
            
        return False