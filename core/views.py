
from django.db.models import Q
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny

# Import all models and serializers needed
from core.models import Faculty, Department, CourseArea, Level, Course
from core.serializers import (
    FacultySerializer, 
    DepartmentSerializer, 
    CourseAreaSerializer, 
    LevelSerializer,  # Import LevelSerializer
    CourseSerializer
)


# --- ViewSets for listing Faculties, Departments, Course Areas, and Levels ---

class FacultyViewSet(ReadOnlyModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [AllowAny]


class DepartmentViewSet(ReadOnlyModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Department.objects.all()
        faculty_id = self.request.query_params.get('faculty_id')
        if faculty_id:
            qs = qs.filter(faculty_id=faculty_id)
        return qs


class CourseAreaViewSet(ReadOnlyModelViewSet):
    serializer_class = CourseAreaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = CourseArea.objects.all()
        department_id = self.request.query_params.get('department_id')
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs


# --- NEW: ViewSet for Levels ---
class LevelViewSet(ReadOnlyModelViewSet):
    serializer_class = LevelSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Returns all levels, optionally filtered by department
        qs = Level.objects.all()
        department_id = self.request.query_params.get('department_id')
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs.order_by('name')


# --- CourseViewSet using IDs ---

class CourseViewSet(ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Course.objects.select_related(
            'level', 'level__department', 'level__department__faculty', 'level__course_area'
        ).order_by('code', 'id')

        params = self.request.query_params

        faculty_id = params.get('faculty_id')
        department_id = params.get('department_id')
        level_id = params.get('level_id') # Changed from level_param to level_id

        if not all([faculty_id, department_id, level_id]):
            return qs.none()

        # --- Build the filter using IDs ---
        final_qs = qs.filter(
            level__department__faculty_id=faculty_id,
            level__department_id=department_id,
            level_id=level_id # Use the level ID directly
        )

        course_area_id = params.get('course_area_id')
        if course_area_id:
            final_qs = final_qs.filter(level__course_area_id=course_area_id)
        else:
            final_qs = final_qs.filter(level__course_area__isnull=True)

        return final_qs
