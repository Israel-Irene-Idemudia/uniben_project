
from django.db.models import Q
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny

from core.models import Course
from core.serializers import CourseSerializer


class CourseViewSet(ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
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

        faculty_id = as_int('faculty_id')
        department_id = as_int('department_id')
        course_area_id = as_int('course_area_id')
        level_id = as_int('level_id')

        # FIX: Use correct query param names sent from the app
        faculty_name = as_str('faculty_name')
        department_name = as_str('department_name')
        course_area_name = as_str('course_area')
        level_param = as_str('level')  # e.g., "100"

        q = Q()

        # Faculty (ID or name)
        if faculty_id:
            q &= Q(level__department__faculty_id=faculty_id)
        elif faculty_name:
            q &= Q(level__department__faculty__name__iexact=faculty_name)

        # Department (ID or name)
        if department_id:
            q &= Q(level__department_id=department_id)
        elif department_name:
            q &= Q(level__department__name__iexact=department_name)

        # Course area (ID or name)
        if course_area_id is not None:
            q &= Q(level__course_area_id=course_area_id)
        elif course_area_name:
            if course_area_name.lower() in ('none', 'null', 'n/a'):
                q &= Q(level__course_area__isnull=True)
            else:
                q &= Q(level__course_area__name__iexact=course_area_name)

        # Level (ID or name like "100L")
        if level_id:
            q &= Q(level_id=level_id)
        # FIX: Use istartswith for more flexible matching (e.g., "100" matches "100L")
        elif level_param:
            q &= Q(level__name__istartswith=level_param)

        # If we have at least one filter, return filtered results
        if q.children:
            return qs.filter(q)

        # No filters provided → return nothing (prevents dumping all courses)
        return qs.none()
