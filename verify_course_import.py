"""
Script to verify that courses were imported correctly to core.Course model.
Run this after the import completes to check the results.
"""

from core.models import Course, Level, Department, Faculty

print("=" * 60)
print("COURSE IMPORT VERIFICATION")
print("=" * 60)

# Check total courses
total_courses = Course.objects.count()
print(f"\n✓ Total courses in core.Course: {total_courses}")

# Check sample courses
if total_courses > 0:
    print("\n📋 Sample courses:")
    for course in Course.objects.all()[:5]:
        print(f"  - {course.code}: {course.title}")
        print(f"    Level: {course.level.name}, Semester: {course.semester}")
        print(f"    Department: {course.level.department.name}")
        print()

# Check levels created
total_levels = Level.objects.count()
print(f"✓ Total levels: {total_levels}")

# Check departments
total_departments = Department.objects.count()
print(f"✓ Total departments: {total_departments}")

# Check faculties
total_faculties = Faculty.objects.count()
print(f"✓ Total faculties: {total_faculties}")

# Check courses by level
print("\n📊 Courses by level:")
for level in Level.objects.all()[:10]:
    course_count = Course.objects.filter(level=level).count()
    print(f"  {level.name} ({level.department.name}): {course_count} courses")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)

# Check if any courses exist in the wrong model (course.Course)
try:
    from course.models import Course as WrongCourse
    wrong_count = WrongCourse.objects.count()
    if wrong_count > 0:
        print(f"\n⚠️  WARNING: {wrong_count} courses in WRONG model (course.Course)")
        print("   These should be deleted or migrated to core.Course")
    else:
        print("\n✓ No courses in wrong model (course.Course)")
except:
    print("\n✓ course.Course model check skipped")
