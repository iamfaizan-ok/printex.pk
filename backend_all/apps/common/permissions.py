from rest_framework.permissions import BasePermission


class IsAdminOrStaff(BasePermission):
    """
    Strict permission class ensuring only authenticated staff or superuser accounts
    can access PrintX admin endpoints.
    """
    message = "Admin or staff privileges required to access this resource."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and
            user.is_authenticated and
            (user.is_staff or user.is_superuser)
        )
