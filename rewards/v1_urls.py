from django.urls import re_path

from .v1_views import V1RedeemView, V1RedemptionListView, V1RewardCatalogView

# Mounted under /api/v1/ in uniben_portal/urls.py.
urlpatterns = [
    re_path(r"^rewards/redeem/?$", V1RedeemView.as_view(), name="v1-rewards-redeem"),
    re_path(r"^rewards/catalog/?$", V1RewardCatalogView.as_view(), name="v1-rewards-catalog"),
    re_path(r"^rewards/redemptions/?$", V1RedemptionListView.as_view(), name="v1-rewards-redemptions"),
]
