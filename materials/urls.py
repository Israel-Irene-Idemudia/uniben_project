from django.urls import path
from .views import MaterialListAPI, MaterialByCategoryAPI, MaterialUploadAPI, MaterialAdminListAPI, MaterialVerificationAPI

urlpatterns = [
    path('materials/', MaterialListAPI.as_view(), name='materials-list'),
    path('materials/upload/', MaterialUploadAPI.as_view(), name='materials-upload'),
    path('materials/<str:category>/', MaterialByCategoryAPI.as_view(), name='materials-by-category'),
    path('admin/materials/list/', MaterialAdminListAPI.as_view(), name='material-admin-list'),
    path('admin/materials/verify/<int:pk>/', MaterialVerificationAPI.as_view(), name='material-verify'),
]
