
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import all the ViewSets
from .views import (
    FacultyViewSet,
    DepartmentViewSet,
    CourseAreaViewSet,
    LevelViewSet,  # Import the new LevelViewSet
    CourseViewSet
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'faculties', FacultyViewSet, basename='faculty')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'course-areas', CourseAreaViewSet, basename='coursearea')
router.register(r'levels', LevelViewSet, basename='level')  # Register the LevelViewSet
router.register(r'courses', CourseViewSet, basename='course')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]
