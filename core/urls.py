from rest_framework import routers
from django.urls import path, include
from core.views import CourseViewSet

router = routers.DefaultRouter()
router.register("courses", CourseViewSet, basename="course")

urlpatterns = [
    path("", include(router.urls)),
]
