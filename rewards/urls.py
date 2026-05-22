from django.urls import path
from .views import (
    RedeemRewardAPI,
    UserRedemptionListAPI,
    AdminRedemptionListAPI,
    AdminRedemptionDispatchAPI,
)

urlpatterns = [
    path('redeem/', RedeemRewardAPI.as_view(), name='redeem-reward'),
    path('redemptions/', UserRedemptionListAPI.as_view(), name='user-redemptions'),
    path('admin/list/', AdminRedemptionListAPI.as_view(), name='admin-redemptions-list'),
    path('admin/dispatch/<int:pk>/', AdminRedemptionDispatchAPI.as_view(), name='admin-redemptions-dispatch'),
]
