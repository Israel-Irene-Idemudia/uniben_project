
from django.db.models import Q
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny

# Import all models needed
from core.models import Faculty, Department, CourseArea, Level, Course
from core.serializers import FacultySerializer, DepartmentSerializer, CourseAreaSerializer, CourseSerializer


# --- New ViewSets to expose IDs ---

class FacultyViewSet(ReadOnlyModelViewSet):
    """
    Provides a read-only list of all faculties.
    """
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [AllowAny]


class DepartmentViewSet(ReadOnlyModelViewSet):
    """
    Provides a read-only list of departments, filterable by faculty_id.
    """
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Department.objects.all()
        faculty_id = self.request.query_params.get('faculty_id')
        if faculty_id:
            qs = qs.filter(faculty_id=faculty_id)
        return qs


class CourseAreaViewSet(ReadOnlyModelViewSet):
    """
    Provides a read-only list of course areas, filterable by department_id.
    """
    serializer_class = CourseAreaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = CourseArea.objects.all()
        department_id = self.request.query_params.get('department_id')
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs


# --- Corrected CourseViewSet using IDs ---

class CourseViewSet(ReadOnlyModelViewSet):
    """
    Filters courses based on provided IDs for faculty, department,
    and optionally course_area, plus the level name.
    """
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Course.objects.select_related(
            'level', 'level__department', 'level__department__faculty', 'level__course_area'
        ).order_by('code', 'id')

        params = self.request.query_params

        # --- Get and validate required ID parameters ---
        try:
            faculty_id = int(params.get('faculty_id'))
            department_id = int(params.get('department_id'))
            level_param = params.get('level', '').strip()
        except (ValueError, TypeError):
            # If required IDs are missing or not integers, return no results.
            return qs.none()

        if not level_param:
            return qs.none()

        # --- Build the filter using precise IDs ---
        final_qs = qs.filter(
            level__department__faculty_id=faculty_id,
            level__department_id=department_id,
        )

        # --- Handle optional Course Area ID ---
        course_area_id_str = params.get('course_area_id', '').strip()
        if course_area_id_str and course_area_id_str.lower() not in ('null', 'none', ''):
            try:
                course_area_id = int(course_area_id_str)
                final_qs = final_qs.filter(level__course_area_id=course_area_id)
            except (ValueError, TypeError):
                return qs.none()  # Invalid course_area_id.
        else:
            # If no course area ID is provided, find courses where it's not set.
            final_qs = final_qs.filter(level__course_area__isnull=True)

        # --- Filter by Level name ---
        final_qs = final_qs.filter(
            Q(level__name__iexact=level_param) | Q(level__name__iexact=f'{level_param}L')
        )

        return final_qs
