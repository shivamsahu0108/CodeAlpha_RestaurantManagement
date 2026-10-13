from rest_framework.permissions import BasePermission, SAFE_METHODS


class StaffWritePermission(BasePermission):
    """
    Allow public read access where appropriate.
    Restrict write operations to authenticated staff.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
