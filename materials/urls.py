from django.urls import path
from .views import MaterialListAPI, MaterialByCategoryAPI

urlpatterns = [
    path('materials/', MaterialListAPI.as_view(), name='materials-list'),
    path('materials/<str:category>/', MaterialByCategoryAPI.as_view(), name='materials-by-category'),
]
