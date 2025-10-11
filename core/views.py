# core/views.py
from django.db.models import Q
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny

from core.models import Course
from core.serializers import CourseSerializer


class CourseViewSet(ReadOnlyModelViewSet):
    """
    API endpoint to list courses with optional filtering by faculty, department,
    course area, and level.
    """
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Base queryset with select_related to optimize DB queries
        qs = Course.objects.select_related(
            'level',
            'level__department',
            'level__department__faculty',
            'level__course_area',
        ).order_by('code', 'id')

        params = self.request.query_params

        def as_int(key):
            v = params.get(key)
            if v is None or v == '':
                return None
            try:
                return int(v)
            except (TypeError, ValueError):
                return None

        def as_str(key):
            v = params.get(key)
            return v.strip() if v else None

        # Extract filters from query parameters
        faculty_id = as_int('faculty_id')
        department_id = as_int('department_id')
        course_area_id = as_int('course_area_id')
        level_id = as_int('level_id')

        faculty_name = as_str('faculty')
        department_name = as_str('department')
        course_area_name = as_str('course_area')
        level_name = as_str('level')

        q = Q()

        # Department filter (takes precedence over faculty)
        if department_id:
            q &= Q(level__department_id=department_id)
        elif department_name:
            q &= Q(level__department__name__iexact=department_name)

        # Faculty filter (only if department wasn’t given)
        if not (department_id or department_name):
            if faculty_id:
                q &= Q(level__department__faculty_id=faculty_id)
            elif faculty_name:
                q &= Q(level__department__faculty__name__iexact=faculty_name)

        # Course area filter
        if course_area_id is not None:
            q &= Q(level__course_area_id=course_area_id)
        elif course_area_name:
            if course_area_name.lower() in ('none', 'null', 'n/a'):
                q &= Q(level__course_area__isnull=True)
            else:
                q &= Q(level__course_area__name__iexact=course_area_name)

        # Level filter
        if level_id:
            q &= Q(level_id=level_id)
        elif level_name:
            q &= Q(level__name__iexact=level_name)

        # Return filtered queryset or empty if no filters
        if q.children:
            return qs.filter(q)

        return qs.none()
