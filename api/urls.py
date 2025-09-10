from django.urls import path, include
from rest_framework import routers
from .views import CourseViewSet, QuestionViewSet

router = routers.DefaultRouter()
router.register(r"courses", CourseViewSet)
router.register(r"questions", QuestionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
