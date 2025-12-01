from rest_framework.permissions import BasePermission, SAFE_METHODS

class CanPostAnonymous(BasePermission):
    # Allows POST if authenticated or a temp_token is supplied (handled in view)
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user and request.user.is_authenticated:
            return True
        # If frontend created temporary token, it should be verified in the view before saving
        temp_token = request.data.get('temp_token') or request.headers.get('X-Temp-Token')
        return bool(temp_token)