from rest_framework import serializers

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