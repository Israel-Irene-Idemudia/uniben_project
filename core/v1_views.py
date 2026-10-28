from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView

from common.pagination import V1PageNumberPagination
from common.views import V1ViewMixin
from core.models import Department, Faculty
from core.v1_serializers import V1DepartmentSerializer, V1FacultySerializer
from rest_framework.permissions import AllowAny


class _PublicRegistryList(V1ViewMixin, ListAPIView):
    """Public on purpose: registration needs these lists before the student
    has an account. Page-number pagination: the registry is a small, stable
    list (D-4). Authentication is off so a stale token cannot cause a 401."""

    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = V1PageNumberPagination


class FacultyListView(_PublicRegistryList):
    serializer_class = V1FacultySerializer

    def get_queryset(self):
        return Faculty.objects.filter(is_active=True).order_by("name", "id")


class DepartmentListView(_PublicRegistryList):
    serializer_class = V1DepartmentSerializer

    def get_queryset(self):
        qs = Department.objects.filter(is_active=True, faculty__is_active=True)
        faculty_id = self.request.query_params.get("faculty_id")
        if faculty_id:
            if not faculty_id.isdigit():
                raise ValidationError({"faculty_id": ["Must be a number."]})
            qs = qs.filter(faculty_id=int(faculty_id))
        return qs.order_by("name", "id")