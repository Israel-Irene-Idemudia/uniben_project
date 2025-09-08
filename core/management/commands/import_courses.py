import csv
from django.core.management.base import BaseCommand
from core.models import Faculty, Department, CourseArea, Level, Course


class Command(BaseCommand):
    help = "Import courses from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")

    def handle(self, *args, **kwargs):
        csv_file = kwargs["csv_file"]

        with open(csv_file, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                # 1. Faculty
                faculty, _ = Faculty.objects.get_or_create(
                    name=row["Faculty"].strip()
                )

                # 2. Department
                department, _ = Department.objects.get_or_create(
                    name=row["Department"].strip(),
                    faculty=faculty
                )

                # 3. Course Area
                course_area, _ = CourseArea.objects.get_or_create(
                    name=row["Course Area"].strip(),
                    department=department
                )

                # 4. Level
                level, _ = Level.objects.get_or_create(
                    name=row["Level"].strip(),
                    department=department,
                    course_area=course_area
                )

                # 5. Course
                Course.objects.update_or_create(
                    code=row["Course Code"].strip(),
                    defaults={
                        "title": row["Course Title"].strip(),
                        "level": level
                    }
                )

        self.stdout.write(self.style.SUCCESS("✅ Courses imported successfully!"))
