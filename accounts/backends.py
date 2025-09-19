from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()

class EmailOrUsernameBackend(ModelBackend):
    """
    This is a custom authentication backend.
    It allows users to log in using their email address or their username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # The 'username' parameter here can be either an email or a username.
        try:
            # Try to fetch the user by treating the 'username' as an email.
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            # If no user is found with that email, try fetching by username.
            try:
                user = UserModel.objects.get(username=username)
            except UserModel.DoesNotExist:
                # If no user is found either way, authentication fails.
                return None

        # If we found a user, we then check their password.
        if user.check_password(password):
            return user
        return None

