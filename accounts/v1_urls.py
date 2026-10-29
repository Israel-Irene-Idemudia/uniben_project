from django.urls import path

from accounts.v1_views import (
    DepartmentChangeView,
    MeProgressView,
    MeView,
    WorldHandoffCreateView,
    WorldHandoffExchangeView,
)

urlpatterns = [
    path("me", MeView.as_view(), name="v1-me"),
    path("me/", MeView.as_view()),
    path("me/progress", MeProgressView.as_view(), name="v1-me-progress"),
    path("me/progress/", MeProgressView.as_view()),
    path("me/department-change", DepartmentChangeView.as_view(), name="v1-department-change"),
    path("me/department-change/", DepartmentChangeView.as_view()),
    path("auth/world-handoff", WorldHandoffCreateView.as_view(), name="v1-world-handoff"),
    path("auth/world-handoff/", WorldHandoffCreateView.as_view()),
    path("auth/world-handoff/exchange", WorldHandoffExchangeView.as_view(), name="v1-world-handoff-exchange"),
    path("auth/world-handoff/exchange/", WorldHandoffExchangeView.as_view()),
]