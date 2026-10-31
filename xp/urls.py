from django.urls import re_path

from .views import MyXPView

# Mounted under /api/v1/ in uniben_portal/urls.py. Catalogue paths have no
# trailing slash; routes accept both (API_CONVENTIONS).
urlpatterns = [
    re_path(r"^me/xp/?$", MyXPView.as_view(), name="v1-me-xp"),
]
