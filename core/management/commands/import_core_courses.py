"""
Django management command to import courses from CSV into core.Course model.
This script imports courses into the CORRECT model (core.Course) that is linked to the frontend.

Now properly handles:
- Matching departments by title (not code)
- Creating/linking CourseAreas
- Creating Levels with course_area FK set
"""

import csv
from django.core.management.base import BaseCommand
from core.models import Course, Level, Department, Faculty, CourseArea


class Command(BaseCommand):
    help = 'Import courses from CSV file into core.Course model (frontend-linked)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='import_data/undergraduate_courses.csv',
            help='Path to the CSV file to import'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to database'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Statistics
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        # Caches to avoid repeated queries
        department_cache = {}
        course_area_cache = {}
        level_cache = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Extract data from CSV
                        course_code = row.get('course_code', '').strip()
                        course_title = row.get('course_title', '').strip()
                        level_int = row.get('level', '').strip()
                        semester_int = row.get('semester', '').strip()
                        
                        # Use TITLE columns for matching (more reliable than codes)
                        department_title = row.get('department_title', '').strip()
                        faculty_title = row.get('faculty_title', '').strip()
                        course_area_code = row.get('course_area_code', '').strip()
                        course_area_title = row.get('course_area_title', '').strip()

                        # Validate required fields
                        if not course_code or not course_title:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Skipping - missing course code or title')
                            )
                            skipped_count += 1
                            continue

                        if not level_int or not semester_int:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Skipping {course_code} - missing level or semester')
                            )
                            skipped_count += 1
                            continue

                        if not department_title:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Skipping {course_code} - missing department_title')
                            )
                            skipped_count += 1
                            continue

                        # Convert to integers
                        try:
                            level_value = int(level_int)
                            semester_value = int(semester_int)
                        except ValueError:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Skipping {course_code} - invalid level or semester value')
                            )
                            skipped_count += 1
                            continue

                        # ============ FIND/CREATE DEPARTMENT ============
                        if department_title in department_cache:
                            department = department_cache[department_title]
                        else:
                            # Try to find department by exact title match
                            department = Department.objects.filter(name__iexact=department_title).first()
                            
                            if not department:
                                # Try contains match for partial titles
                                department = Department.objects.filter(name__icontains=department_title[:20]).first()
                            
                            if not department:
                                self.stdout.write(
                                    self.style.WARNING(f'Row {row_num}: Skipping {course_code} - department "{department_title}" not found in DB')
                                )
                                skipped_count += 1
                                continue
                            
                            department_cache[department_title] = department

                        # ============ FIND/CREATE COURSE AREA ============
                        course_area = None
                        if course_area_title:
                            ca_cache_key = f"{department.id}_{course_area_title}"
                            
                            if ca_cache_key in course_area_cache:
                                course_area = course_area_cache[ca_cache_key]
                            else:
                                # Try to find existing course area
                                course_area = CourseArea.objects.filter(
                                    department=department,
                                    name__iexact=course_area_title
                                ).first()
                                
                                if not course_area and not dry_run:
                                    # Create the course area
                                    course_area = CourseArea.objects.create(
                                        name=course_area_title,
                                        department=department
                                    )
                                    self.stdout.write(
                                        self.style.SUCCESS(f'Created CourseArea: {course_area_title} for {department.name}')
                                    )
                                
                                if course_area:
                                    course_area_cache[ca_cache_key] = course_area

                        # ============ FIND/CREATE LEVEL ============
                        level_name = f"{level_value}L"  # e.g. "100L", "200L"
                        
                        # Cache key includes course_area to create separate levels per area
                        level_cache_key = f"{department.id}_{course_area.id if course_area else 'none'}_{level_name}"

                        if level_cache_key in level_cache:
                            level_obj = level_cache[level_cache_key]
                        else:
                            # Try to find existing level with matching course_area
                            level_obj = Level.objects.filter(
                                department=department,
                                course_area=course_area,  # Can be None
                                name=level_name
                            ).first()
                            
                            if not level_obj and not dry_run:
                                # Create the level with course_area
                                level_obj = Level.objects.create(
                                    name=level_name,
                                    department=department,
                                    course_area=course_area
                                )
                                ca_info = f" ({course_area.name})" if course_area else ""
                                self.stdout.write(
                                    self.style.SUCCESS(f'Created Level: {level_name} for {department.name}{ca_info}')
                                )
                            elif dry_run and not level_obj:
                                self.stdout.write(
                                    self.style.WARNING(f'Would create Level: {level_name} for {department.name}')
                                )
                                skipped_count += 1
                                continue
                            
                            if level_obj:
                                level_cache[level_cache_key] = level_obj

                        # ============ CREATE/UPDATE COURSE ============
                        if not dry_run and level_obj:
                            course, created = Course.objects.update_or_create(
                                level=level_obj,
                                code=course_code,
                                semester=semester_value,
                                defaults={
                                    'title': course_title,
                                }
                            )

                            if created:
                                created_count += 1
                                if created_count % 500 == 0:
                                    self.stdout.write(
                                        self.style.SUCCESS(f'Progress: Created {created_count} courses...')
                                    )
                            else:
                                updated_count += 1
                        else:
                            # Dry run
                            created_count += 1

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Row {row_num}: Error processing {course_code}: {str(e)}')
                        )

                # Summary
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.SUCCESS('IMPORT SUMMARY'))
                self.stdout.write('='*60)
                if dry_run:
                    self.stdout.write(f'Would create: {created_count} courses')
                    self.stdout.write(f'Would update: {updated_count} courses')
                else:
                    self.stdout.write(self.style.SUCCESS(f'Created: {created_count} courses'))
                    self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count} courses'))
                self.stdout.write(f'Skipped: {skipped_count} rows')
                self.stdout.write(self.style.ERROR(f'Errors: {error_count} rows'))
                self.stdout.write('='*60)

        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading file: {str(e)}')
            )
