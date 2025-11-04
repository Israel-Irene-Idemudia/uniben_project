
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
            'level', 'level__department', 'level__department__faculty', 'level__course_area'
        ).order_by('code', 'id')

        params = self.request.query_params

        faculty_name = params.get('faculty_name', '').strip()
        department_name = params.get('department_name', '').strip()
        course_area_name = params.get('course_area', '').strip()
        level_param = params.get('level', '').strip()

        # If essential filters are missing, return nothing.
        if not all([faculty_name, department_name, level_param]):
            return qs.none()

        # Start with a queryset that can be filtered.
        final_qs = qs

        # --- Build the filter step-by-step for clarity and correctness ---

        # 1. Filter by Faculty
        final_qs = final_qs.filter(level__department__faculty__name__iexact=faculty_name)

        # 2. Filter by Department
        final_qs = final_qs.filter(level__department__name__iexact=department_name)

        # 3. Filter by Course Area (if it exists)
        if course_area_name and course_area_name.lower() not in ('none', 'null', 'n/a', ''):
            final_qs = final_qs.filter(level__course_area__name__iexact=course_area_name)
        else:
            # If no course area is specified in the user's profile,
            # then only find courses where the level's course area is also not set.
            final_qs = final_qs.filter(level__course_area__isnull=True)

        # 4. Filter by Level
        # This handles both "100" (from the app) and "100L" (a possible DB format)
        final_qs = final_qs.filter(
            Q(level__name__iexact=level_param) | Q(level__name__iexact=f'{level_param}L')
        )

        # If any of the above filters resulted in an empty set, the result will be empty.
        # Otherwise, we have our matching courses.
        return final_qs
