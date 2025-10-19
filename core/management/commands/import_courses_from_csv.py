# core/management/commands/import_courses_clean.py
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Faculty, Department, CourseArea, Level, Course

class Command(BaseCommand):
    help = "Import courses from CSV with detailed logging"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            required=True,
            help="Path to CSV file",
        )

    def clean_text(self, text):
        return text.strip() if text else ""

    @transaction.atomic
    def handle(self, *args, **opts):
        import csv
        path = opts["path"]
        
        created_counts = {
            'faculty': 0,
            'department': 0,
            'course_area': 0,
            'level': 0,
            'course': 0
        }

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Clean data
                faculty_name = self.clean_text(row['Faculty'])
                department_name = self.clean_text(row['Department'])
                course_area_name = self.clean_text(row['Course Area'])
                level_name = self.clean_text(row['Level'])
                course_code = self.clean_text(row['Course Code'])
                course_title = self.clean_text(row['Course Title'])

                try:
                    # Create Faculty
                    faculty, created = Faculty.objects.get_or_create(
                        name=faculty_name
                    )
                    if created:
                        created_counts['faculty'] += 1
                        self.stdout.write(f"Created faculty: {faculty_name}")

                    # Create Department
                    department, created = Department.objects.get_or_create(
                        name=department_name,
                        faculty=faculty
                    )
                    if created:
                        created_counts['department'] += 1
                        self.stdout.write(f"Created department: {department_name}")

                    # Create Course Area
                    course_area = None
                    if course_area_name:
                        course_area, created = CourseArea.objects.get_or_create(
                            name=course_area_name,
                            department=department
                        )
                        if created:
                            created_counts['course_area'] += 1
                            self.stdout.write(f"Created course area: {course_area_name}")

                    # Create Level
                    level, created = Level.objects.get_or_create(
                        name=level_name,
                        department=department,
                        course_area=course_area
                    )
                    if created:
                        created_counts['level'] += 1
                        self.stdout.write(f"Created level: {level_name} for {department_name}")

                    # Create Course
                    course, created = Course.objects.get_or_create(
                        code=course_code,
                        level=level,
                        defaults={'title': course_title}
                    )
                    if created:
                        created_counts['course'] += 1
                        self.stdout.write(f"Created course: {course_code} - {course_title}")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error processing row: {row}\nError: {str(e)}"
                    ))

        # Print summary
        self.stdout.write(self.style.SUCCESS("\nImport Summary:"))
        self.stdout.write(f"Faculties created: {created_counts['faculty']}")
        self.stdout.write(f"Departments created: {created_counts['department']}")
        self.stdout.write(f"Course Areas created: {created_counts['course_area']}")
        self.stdout.write(f"Levels created: {created_counts['level']}")
        self.stdout.write(f"Courses created: {created_counts['course']}")