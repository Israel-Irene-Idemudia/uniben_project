
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


# --- Corrected CourseViewSet using Names ---

class CourseViewSet(ReadOnlyModelViewSet):
    """
    Filters courses based on provided names for faculty, department,
    and optionally course_area, plus the level name.
    """
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Course.objects.select_related(
            'level', 'level__department', 'level__department__faculty', 'level__course_area'
        ).order_by('code', 'id')

        params = self.request.query_params

        # --- Get and validate required NAME parameters ---
        faculty_name = params.get('faculty__name', '').strip()
        department_name = params.get('department__name', '').strip()
        level_param = params.get('level', '').strip()

        if not all([faculty_name, department_name, level_param]):
            # If required names are missing, return no results.
            return qs.none()

        # --- Build the filter using names (case-insensitive) ---
        final_qs = qs.filter(
            level__department__faculty__name__iexact=faculty_name,
            level__department__name__iexact=department_name,
        )

        # --- Handle optional Course Area name ---
        course_area_name = params.get('course_area', '').strip()
        if course_area_name and course_area_name.lower() not in ('null', 'none', ''):
            final_qs = final_qs.filter(level__course_area__name__iexact=course_area_name)
        else:
            # If no course area name is provided, find courses where it's not set.
            final_qs = final_qs.filter(level__course_area__isnull=True)

        # --- Filter by Level name (handles "100" and "100L") ---
        final_qs = final_qs.filter(
            Q(level__name__iexact=level_param) | Q(level__name__iexact=f'{level_param}L')
        )

        return final_qs
