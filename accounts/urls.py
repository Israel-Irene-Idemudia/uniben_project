from django.urls import path
from .views import RegisterView, UpdateProfileView, MeView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path('me/', MeView.as_view(), name='me'),
    path("profile/update/", UpdateProfileView.as_view(), name="update_profile"),
]
