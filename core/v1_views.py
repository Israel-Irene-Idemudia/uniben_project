from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView

from common.pagination import V1PageNumberPagination
from common.views import V1ViewMixin
from core.models import Department, Faculty, University
from core.v1_serializers import V1DepartmentSerializer, V1FacultySerializer, V1UniversitySerializer
from rest_framework.permissions import AllowAny


def _int_param(request, name):
    """Optional numeric query parameter, validated in the v1 error shape."""
    value = request.query_params.get(name)
    if not value:
        return None
    if not value.isdigit():
        raise ValidationError({name: ["Must be a number."]})
    return int(value)


class _PublicRegistryList(V1ViewMixin, ListAPIView):
    """Public on purpose: registration needs these lists before the student
    has an account. Page-number pagination: the registry is a small, stable
    list (D-4). Authentication is off so a stale token cannot cause a 401."""

    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = V1PageNumberPagination


class UniversityListView(_PublicRegistryList):
    serializer_class = V1UniversitySerializer

    def get_queryset(self):
        return University.objects.filter(is_active=True).order_by("name", "id")


class FacultyListView(_PublicRegistryList):
    serializer_class = V1FacultySerializer

    def get_queryset(self):
        qs = Faculty.objects.filter(is_active=True)
        university_id = _int_param(self.request, "university_id")
        if university_id is not None:
            qs = qs.filter(university_id=university_id, university__is_active=True)
        return qs.order_by("name", "id")


class DepartmentListView(_PublicRegistryList):
    serializer_class = V1DepartmentSerializer

    def get_queryset(self):
        qs = Department.objects.filter(is_active=True, faculty__is_active=True)
        faculty_id = _int_param(self.request, "faculty_id")
        if faculty_id is not None:
            qs = qs.filter(faculty_id=faculty_id)
        university_id = _int_param(self.request, "university_id")
        if university_id is not None:
            qs = qs.filter(faculty__university_id=university_id)
        return qs.order_by("name", "id")