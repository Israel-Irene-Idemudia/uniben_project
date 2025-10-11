# core/urls.py
from rest_framework.routers import DefaultRouter
from core.views import CourseViewSet

router = DefaultRouter()
router.register('courses', CourseViewSet, basename='courses')

urlpatterns = router.urls