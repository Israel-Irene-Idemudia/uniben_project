"""
Django management command to import courses from CSV into core.Course model.
This script imports courses into the CORRECT model (core.Course) that is linked to the frontend.
"""

import csv
from django.core.management.base import BaseCommand
from core.models import Course, Level, Department, Faculty


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
        
        # Cache for Level objects to avoid repeated queries
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
                        department_code = row.get('department_code', '').strip()
                        faculty_code = row.get('faculty_code', '').strip()

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

                        # Convert to integers
                        try:
                            level_value = int(level_int)
                            semester_value = int(semester_int)
                        except ValueError:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Skipping {course_code} - invalid level or semester')
                            )
                            skipped_count += 1
                            continue

                        # Find or create the Level object
                        # The Level model has: name (e.g. "100L"), department (ForeignKey)
                        # We need to match based on the level number
                        
                        level_name = f"{level_value}L"  # e.g. "100L", "200L"
                        cache_key = f"{department_code}_{level_name}"

                        if cache_key in level_cache:
                            level_obj = level_cache[cache_key]
                        else:
                            # Try to find the Level object
                            # First, try to find by department code and level name
                            try:
                                department = Department.objects.filter(name__icontains=department_code).first()
                                if not department:
                                    # Try finding by faculty
                                    faculty = Faculty.objects.filter(name__icontains=faculty_code).first()
                                    if faculty:
                                        department = faculty.departments.first()
                                
                                if department:
                                    level_obj = Level.objects.filter(
                                        department=department,
                                        name=level_name
                                    ).first()
                                    
                                    if not level_obj:
                                        # Create the level if it doesn't exist
                                        if not dry_run:
                                            level_obj = Level.objects.create(
                                                name=level_name,
                                                department=department
                                            )
                                            self.stdout.write(
                                                self.style.SUCCESS(f'Created Level: {level_name} for {department.name}')
                                            )
                                        else:
                                            self.stdout.write(
                                                self.style.WARNING(f'Would create Level: {level_name} for {department.name}')
                                            )
                                            skipped_count += 1
                                            continue
                                    
                                    level_cache[cache_key] = level_obj
                                else:
                                    self.stdout.write(
                                        self.style.WARNING(f'Row {row_num}: Could not find department for {course_code}')
                                    )
                                    skipped_count += 1
                                    continue
                                    
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(f'Row {row_num}: Error finding level for {course_code}: {str(e)}')
                                )
                                error_count += 1
                                continue

                        # Create or update the course
                        if not dry_run:
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
                                self.stdout.write(
                                    self.style.SUCCESS(f'Row {row_num}: Created {course_code} - {course_title}')
                                )
                            else:
                                updated_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'Row {row_num}: Updated {course_code} - {course_title}')
                                )
                        else:
                            # Dry run - check if exists
                            exists = Course.objects.filter(
                                level=level_obj,
                                code=course_code,
                                semester=semester_value
                            ).exists()
                            
                            if exists:
                                updated_count += 1
                                self.stdout.write(f'Row {row_num}: Would update {course_code}')
                            else:
                                created_count += 1
                                self.stdout.write(f'Row {row_num}: Would create {course_code}')

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Row {row_num}: Error processing {course_code}: {str(e)}')
                        )

                # Summary
                self.stdout.write('\\n' + '='*60)
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
