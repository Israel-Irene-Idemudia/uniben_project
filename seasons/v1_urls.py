from django.urls import path

from .views import CurrentSeasonView

urlpatterns = [
    path("seasons/current", CurrentSeasonView.as_view(), name="v1-seasons-current"),
    path("seasons/current/", CurrentSeasonView.as_view()),
]
