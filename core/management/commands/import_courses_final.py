import csv
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Course, Level, Department, CourseArea, Faculty

class Command(BaseCommand):
    help = 'Import courses using Names (Legacy Mode)'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='import_data/latest version.csv')

    def handle(self, *args, **options):
        file_path = options['file']
        
        created_count = 0
        skipped_count = 0

        try:
            self.stdout.write(f"Reading file: {file_path}...")
            
            with open(file_path, 'r', encoding='utf-8-sig') as csvfile: 
                reader = csv.DictReader(csvfile)
                
                # Atomic transaction ensures we don't get half-imported garbage if it crashes
                with transaction.atomic():
                    for row_num, row in enumerate(reader, start=2):
                        try:
                            # --- 1. Extract Data ---
                            # We use the titles because your models lack 'code' fields
                            f_title = row.get('faculty_title', '').strip()
                            d_title = row.get('department_title', '').strip()
                            c_area_title = row.get('course_area_title', '').strip()
                            
                            course_code = row.get('course_code', '').strip()
                            course_title = row.get('course_title', '').strip()
                            
                            # Regex to safely extract numbers
                            level_raw = row.get('level', '')
                            semester_raw = row.get('semester', '')
                            level_match = re.search(r'\d+', str(level_raw))
                            sem_match = re.search(r'\d+', str(semester_raw))

                            # Validation: We need at least Faculty, Dept, Course Code, and Level
                            if not (f_title and d_title and course_code and level_match):
                                self.stdout.write(self.style.WARNING(f"Row {row_num}: Missing essential data. Skipped."))
                                skipped_count += 1
                                continue

                            level_val = int(level_match.group())
                            semester_val = int(sem_match.group()) if sem_match else 1

                            # --- 2. Get or Create Faculty ---
                            # Matches exactly on the name string from CSV
                            faculty, _ = Faculty.objects.get_or_create(
                                name=f_title
                            )

                            # --- 3. Get or Create Department ---
                            department, _ = Department.objects.get_or_create(
                                faculty=faculty,
                                name=d_title
                            )

                            # --- 4. Get or Create Course Area (Optional) ---
                            course_area = None
                            if c_area_title:
                                course_area, _ = CourseArea.objects.get_or_create(
                                    department=department,
                                    name=c_area_title
                                )

                            # --- 5. Get or Create Level ---
                            # Level name format: "100L"
                            level_str = f"{level_val}L"
                            
                            # Construct lookup arguments based on your model constraints
                            level_kwargs = {
                                'department': department,
                                'course_area': course_area,
                                'name': level_str,
                            }
                            
                            level_obj, _ = Level.objects.get_or_create(**level_kwargs)

                            # --- 6. Create or Update Course ---
                            # Your constraint is ['level', 'code', 'semester']
                            Course.objects.update_or_create(
                                level=level_obj,
                                code=course_code,
                                semester=semester_val,
                                defaults={'title': course_title}
                            )
                            created_count += 1

                            if row_num % 500 == 0:
                                self.stdout.write(f"Processed {row_num} rows...")

                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Row {row_num}: Error - {str(e)}"))

            self.stdout.write(self.style.SUCCESS(f"\nImport Complete! Created/Updated: {created_count}, Skipped: {skipped_count}"))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}. Please check the path."))