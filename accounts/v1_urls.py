from django.urls import path

from accounts.v1_views import MeProgressView, MeView

urlpatterns = [
    path("me", MeView.as_view(), name="v1-me"),
    path("me/", MeView.as_view()),
    path("me/progress", MeProgressView.as_view(), name="v1-me-progress"),
    path("me/progress/", MeProgressView.as_view()),
]