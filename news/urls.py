
from django.urls import path
from .views import NewsListAPI, NewsDetailAPI

urlpatterns = [
    path('news/', NewsListAPI.as_view(), name='api_news_list'),
    path('news/<int:pk>/', NewsDetailAPI.as_view(), name='api_news_detail'),
]
