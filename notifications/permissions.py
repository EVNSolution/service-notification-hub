from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission


def ensure_authenticated(request):
    user = request.user
    if not (user and getattr(user, "is_authenticated", False)):
        raise NotAuthenticated("Authentication credentials were not provided.")
    return user


def is_admin(user) -> bool:
    return getattr(user, "role", "user") == "admin"


class AuthenticatedNotificationAccess(BasePermission):
    def has_permission(self, request, view) -> bool:
        ensure_authenticated(request)
        return True


class AdminOnlyAccess(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = ensure_authenticated(request)
        if not is_admin(user):
            raise PermissionDenied("Admin role required.")
        return True
