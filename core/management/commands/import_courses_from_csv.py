# core/management/commands/import_courses_from_csv.py

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Faculty, Department, CourseArea, Level, Course
import csv
import os

class Command(BaseCommand):
    help = "Import courses from a CSV with headers: Level, Semester, Course Code, Course Title, Course Area, Department, Faculty"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            required=True,
            help="Path to CSV file",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update course title if a course with the same (level, code) already exists",
        )
        parser.add_argument(
            "--encoding",
            default="utf-8",
            help="CSV encoding (default: utf-8)",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]
        update = opts["update"]
        encoding = opts["encoding"]

        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        created_fac = created_dep = created_area = created_lvl = created_crs = 0
        updated_crs = 0
        total_rows = 0

        with open(path, "r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            required_headers = [
                "Level",
                "Semester",       # we will read but not store (you can add later if needed)
                "Course Code",
                "Course Title",
                "Course Area",    # may be empty
                "Department",
                "Faculty",
            ]
            missing = [h for h in required_headers if h not in (reader.fieldnames or [])]
            if missing:
                self.stderr.write(self.style.ERROR(f"CSV missing headers: {', '.join(missing)}"))
                return

            for row_idx, row in enumerate(reader, start=2):
                total_rows += 1

                level_name = (row.get("Level") or "").strip()          # e.g., "100L"
                # semester = (row.get("Semester") or "").strip()       # read if needed later
                code = (row.get("Course Code") or "").strip().upper()
                title = (row.get("Course Title") or "").strip()
                course_area_name = (row.get("Course Area") or "").strip()
                department_name = (row.get("Department") or "").strip()
                faculty_name = (row.get("Faculty") or "").strip()

                if not (level_name and code and title and department_name and faculty_name):
                    self.stderr.write(self.style.WARNING(f"Row {row_idx}: missing required values; skipped"))
                    continue

                # Faculty
                faculty, fac_created = Faculty.objects.get_or_create(name=faculty_name)
                if fac_created:
                    created_fac += 1

                # Department (scoped by faculty)
                department, dep_created = Department.objects.get_or_create(
                    name=department_name, faculty=faculty
                )
                if dep_created:
                    created_dep += 1

                # Course area (optional)
                course_area = None
                if course_area_name:
                    course_area, area_created = CourseArea.objects.get_or_create(
                        name=course_area_name, department=department
                    )
                    if area_created:
                        created_area += 1

                # Level (scoped by department + course_area)
                level, lvl_created = Level.objects.get_or_create(
                    name=level_name,
                    department=department,
                    course_area=course_area,
                )
                if lvl_created:
                    created_lvl += 1

                # Course (unique by level + code)
                course, crs_created = Course.objects.get_or_create(
                    level=level,
                    code=code,
                    defaults={"title": title},
                )
                if crs_created:
                    created_crs += 1
                elif update and course.title != title:
                    course.title = title
                    course.save(update_fields=["title"])
                    updated_crs += 1

        self.stdout.write(self.style.SUCCESS("Import complete"))
        self.stdout.write(f"Rows processed: {total_rows}")
        self.stdout.write(f"Created: Faculty={created_fac}, Department={created_dep}, CourseArea={created_area}, Level={created_lvl}, Course={created_crs}")
        if update:
            self.stdout.write(f"Updated course titles: {updated_crs}")