from rest_framework.permissions import BasePermission

from accounts.account_state import ACTIVE, get_account_state


class IsNotSuspended(BasePermission):
    """Block suspended (or deleted) accounts from social and competitive
    features (BE-01.5). Put it AFTER IsAuthenticated in permission_classes:
    permission_classes = [IsAuthenticated, IsNotSuspended].
    """

    message = "Your account is suspended from this feature."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return True  # IsAuthenticated decides, so anonymous callers still get 401
        return get_account_state(user) == ACTIVE