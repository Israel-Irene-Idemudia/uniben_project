from django.urls import path

from .password_reset_views import ResetConfirmView, ResetRequestView, ResetValidateView

urlpatterns = [
    path("validate_token/", ResetValidateView.as_view(), name="reset-password-validate"),
    path("confirm/", ResetConfirmView.as_view(), name="reset-password-confirm"),
    path("", ResetRequestView.as_view(), name="reset-password-request"),
]