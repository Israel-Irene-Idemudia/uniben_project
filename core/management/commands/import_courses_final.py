import csv
import re
from django.core.management.base import BaseCommand
from core.models import Course, Level, Department, CourseArea, Faculty

class Command(BaseCommand):
    help = 'Import courses with strict matching and CourseArea support'

    def add_arguments(self, parser):
        # Default points to the file inside an 'import_data' folder in your root
        parser.add_argument('--file', type=str, default='import_data/latest version.csv')

    def handle(self, *args, **options):
        file_path = options['file']
        
        # 1. Load Caches (Speed up the script by 100x)
        # We normalize DB names to lowercase and remove "department of" for easier matching
        dept_cache = {d.name.lower().replace('department of', '').strip(): d for d in Department.objects.all()}
        faculty_cache = {f.name.lower().strip(): f for f in Faculty.objects.all()}
        
        created_count = 0
        skipped_count = 0

        try:
            self.stdout.write(f"Reading file: {file_path}...")
            
            with open(file_path, 'r', encoding='utf-8-sig') as csvfile: 
                # 'utf-8-sig' handles the BOM if Excel added one
                reader = csv.DictReader(csvfile)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # --- 2. Extract Data Safely ---
                        course_code = row.get('course_code', '').strip()
                        course_title = row.get('course_title', '').strip()
                        dept_name_raw = row.get('department_title', '').strip()
                        faculty_name_raw = row.get('faculty_title', '').strip()
                        
                        # HANDLE THE CSV DIFFERENCE: Check both column names
                        area_name = row.get('course_area_title', '').strip() or row.get('certificate_title', '').strip()

                        # Extract numbers from Level/Semester using Regex (Safe for "100 Level")
                        level_raw = row.get('level', '')
                        semester_raw = row.get('semester', '')
                        
                        level_match = re.search(r'\d+', str(level_raw))
                        sem_match = re.search(r'\d+', str(semester_raw))

                        # Skip bad rows
                        if not (course_code and course_title and dept_name_raw and level_match and sem_match):
                            self.stdout.write(self.style.WARNING(f"Row {row_num}: Missing essential data. Skipped."))
                            skipped_count += 1
                            continue

                        level_val = int(level_match.group())
                        semester_val = int(sem_match.group())

                        # --- 3. Strict Department Matching (NO GUESSING) ---
                        target_dept = None
                        
                        # Normalize the CSV department name
                        norm_dept_csv = dept_name_raw.lower().replace('department of', '').strip()
                        
                        # Attempt 1: Check the cache for an exact match
                        if norm_dept_csv in dept_cache:
                            target_dept = dept_cache[norm_dept_csv]
                        
                        # Attempt 2: Filter by Faculty (The Safety Net)
                        # If exact match failed, look inside the specific Faculty to avoid cross-faculty errors
                        if not target_dept and faculty_name_raw:
                            norm_faculty_csv = faculty_name_raw.lower().strip()
                            target_faculty = None
                            
                            # Find the faculty object
                            for f_name, f_obj in faculty_cache.items():
                                if norm_faculty_csv in f_name or f_name in norm_faculty_csv:
                                    target_faculty = f_obj
                                    break
                            
                            if target_faculty:
                                # Look for the department ONLY inside this faculty
                                potential_depts = Department.objects.filter(faculty=target_faculty)
                                for dept in potential_depts:
                                    # Strict substring match
                                    if norm_dept_csv in dept.name.lower():
                                        target_dept = dept
                                        break

                        if not target_dept:
                            self.stdout.write(self.style.ERROR(f"Row {row_num}: Dept '{dept_name_raw}' not found in DB. Skipped."))
                            skipped_count += 1
                            continue

                        # --- 4. Handle Course Area ---
                        target_area = None
                        if area_name:
                            target_area, _ = CourseArea.objects.get_or_create(
                                department=target_dept,
                                name__iexact=area_name,
                                defaults={'name': area_name}
                            )

                        # --- 5. Handle Level ---
                        # We link the Level to the Course Area.
                        # This means "100L (Agric)" is different from "100L (Education)"
                        level_str = f"{level_val}L"
                        target_level, _ = Level.objects.get_or_create(
                            department=target_dept,
                            name=level_str,
                            course_area=target_area 
                        )

                        # --- 6. Create/Update the Course ---
                        Course.objects.update_or_create(
                            level=target_level,
                            code=course_code,
                            semester=semester_val,
                            defaults={'title': course_title}
                        )
                        created_count += 1

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Row {row_num}: Error - {str(e)}"))

            self.stdout.write(self.style.SUCCESS(f"\nImport Complete! Processed: {created_count}, Skipped: {skipped_count}"))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}. Please check the path."))
