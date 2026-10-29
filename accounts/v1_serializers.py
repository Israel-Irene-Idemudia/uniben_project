from rest_framework import serializers
from core.models import Department, Level

# Fields that must go through a dedicated, audited endpoint instead.
_DEPARTMENT_KEYS = {"faculty", "faculty_id", "department", "department_id", "level", "level_id", "course_area", "course_area_id"}


class MeUpdateSerializer(serializers.Serializer):
    """Fields a student may change on their own record via PATCH /me.

    Anything not listed is rejected, not silently ignored: a client must never
    think it changed points, XP or a department when it did not (D7).
    """

    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.RegexField(
        r"^[0-9+()\-\s]*$", max_length=20, required=False, allow_blank=True,
        error_messages={"invalid": "Use digits, spaces, +, - and brackets only."},
    )
    network = serializers.CharField(max_length=15, required=False, allow_blank=True)
    student_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    matric_number = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def to_internal_value(self, data):
        errors = {}
        for key in data:
            if key in self.fields:
                continue
            if key in _DEPARTMENT_KEYS:
                errors[key] = ["Cannot be changed here. Use POST /api/v1/me/department-change."]
            else:
                errors[key] = ["This field cannot be changed."]
        if errors:
            raise serializers.ValidationError(errors)
        return super().to_internal_value(data)

class DepartmentChangeSerializer(serializers.Serializer):
    department_id = serializers.IntegerField()
    level_id = serializers.IntegerField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_department_id(self, value):
        try:
            self._department = Department.objects.select_related("faculty").get(
                pk=value, is_active=True, faculty__is_active=True
            )
        except Department.DoesNotExist:
            raise serializers.ValidationError("Unknown or inactive department.")
        return value

    def validate(self, attrs):
        level = None
        level_id = attrs.get("level_id")
        if level_id is not None:
            level = (
                Level.objects.select_related("course_area")
                .filter(pk=level_id, department_id=self._department.pk)
                .first()
            )
            if level is None:
                raise serializers.ValidationError(
                    {"level_id": ["This level does not belong to the chosen department."]}
                )
        attrs["department"] = self._department
        attrs["level"] = level
        return attrs