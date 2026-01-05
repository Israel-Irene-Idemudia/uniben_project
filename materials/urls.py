from django.urls import path
from .views import MaterialListAPI, MaterialByCategoryAPI, MaterialUploadAPI

urlpatterns = [
    path('materials/', MaterialListAPI.as_view(), name='materials-list'),
    path('materials/upload/', MaterialUploadAPI.as_view(), name='materials-upload'),
    path('materials/<str:category>/', MaterialByCategoryAPI.as_view(), name='materials-by-category'),
]
