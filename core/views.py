
from django.db.models import Q
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny

# Import all models and serializers needed
from core.models import Faculty, Department, CourseArea, Level, Course
from core.serializers import (
    FacultySerializer, 
    DepartmentSerializer, 
    CourseAreaSerializer, 
    LevelSerializer,
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


class LevelViewSet(ReadOnlyModelViewSet):
    serializer_class = LevelSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Dynamically filters levels based on faculty, department, and course area.
        - If `department_id` is provided, it filters levels for that department.
        - If `course_area_id` is also provided, it further refines the filter.
        - This allows the frontend to get a context-specific list of levels.
        """
        qs = Level.objects.all()

        # Get filter parameters from the request
        department_id = self.request.query_params.get('department_id')
        course_area_id = self.request.query_params.get('course_area_id')

        # A level is linked to a department and optionally to a course area.
        # So, the primary filter is the department.
        if department_id:
            qs = qs.filter(department_id=department_id)

            # If a course area is also specified, filter by that as well.
            # If not, we should only return levels that DON'T have a course area.
            if course_area_id:
                qs = qs.filter(course_area_id=course_area_id)
            else:
                # This ensures we don't accidentally return levels that are 
                # specific to a course area.
                qs = qs.filter(course_area__isnull=True)

        else:
            # If no department is specified, it doesn't make sense to return any levels.
            return qs.none()

        return qs.order_by('name')


class CourseViewSet(ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Course.objects.select_related(
            'level', 'level__department', 'level__course_area'
        ).order_by('code', 'id')

        params = self.request.query_params

        department_id = params.get('department_id')
        level_id = params.get('level_id')

        # We must have a department and a level to find courses
        if not all([department_id, level_id]):
            return qs.none()

        # --- Build the filter using IDs ---
        final_qs = qs.filter(
            level__department_id=department_id,
            level_id=level_id
        )

        course_area_id = params.get('course_area_id')
        if course_area_id:
            final_qs = final_qs.filter(level__course_area_id=course_area_id)
        else:
            # If no course area, only get courses where the level isn't 
            # linked to a course area.
            final_qs = final_qs.filter(level__course_area__isnull=True)

        return final_qs
