# core/management/commands/check_csv.py
from django.core.management.base import BaseCommand
import csv

class Command(BaseCommand):
    help = "Check CSV data structure"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            required=True,
            help="Path to CSV file",
        )

    def handle(self, *args, **opts):
        path = opts["path"]
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Print headers
            self.stdout.write("CSV Headers:")
            self.stdout.write(str(reader.fieldnames))
            
            # Print first 3 rows
            self.stdout.write("\nFirst 3 rows:")
            for i, row in enumerate(reader):
                if i < 3:
                    self.stdout.write(str(row))
                else:
                    break

            # Print counts
            f.seek(0)
            next(reader)  # Skip header
            faculties = set()
            departments = set()
            course_areas = set()
            levels = set()
            courses = set()
            
            for row in reader:
                faculties.add(row['Faculty'])
                departments.add(row['Department'])
                if row['Course Area']:
                    course_areas.add(row['Course Area'])
                levels.add(row['Level'])
                courses.add(row['Course Code'])
            
            self.stdout.write("\nUnique counts:")
            self.stdout.write(f"Faculties: {len(faculties)}")
            self.stdout.write(f"Departments: {len(departments)}")
            self.stdout.write(f"Course Areas: {len(course_areas)}")
            self.stdout.write(f"Levels: {len(levels)}")
            self.stdout.write(f"Courses: {len(courses)}")