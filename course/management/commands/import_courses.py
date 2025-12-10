import csv
from django.core.management.base import BaseCommand
from course.models import Course


class Command(BaseCommand):
    help = 'Import courses from undergraduate_courses.csv file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='import_data/undergraduate_courses.csv',
            help='Path to the CSV file to import (relative to project root)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any changes to the database'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made to the database'))
        
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                created_count = 0
                updated_count = 0
                skipped_count = 0
                error_count = 0
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header
                    try:
                        course_code = row.get('course_code', '').strip()
                        
                        if not course_code:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Skipping - no course code')
                            )
                            skipped_count += 1
                            continue
                        
                        # Parse level (convert to integer)
                        level = None
                        if row.get('level'):
                            try:
                                level = int(row['level'])
                            except ValueError:
                                self.stdout.write(
                                    self.style.WARNING(f'Row {row_num}: Invalid level value "{row["level"]}" for {course_code}')
                                )
                        
                        # Parse semester (convert to integer)
                        semester = None
                        if row.get('semester'):
                            try:
                                semester = int(row['semester'])
                            except ValueError:
                                self.stdout.write(
                                    self.style.WARNING(f'Row {row_num}: Invalid semester value "{row["semester"]}" for {course_code}')
                                )
                        
                        # Prepare course data
                        course_data = {
                            'title': row.get('course_title', '').strip() or None,
                            'level': level,
                            'semester': semester,
                            'faculty_code': row.get('faculty_code', '').strip() or None,
                            'faculty_title': row.get('faculty_title', '').strip() or None,
                            'department_code': row.get('department_code', '').strip() or None,
                            'department_title': row.get('department_title', '').strip() or None,
                            'certificate_code': row.get('certificate_code', '').strip() or None,
                            'certificate_title': row.get('certificate_title', '').strip() or None,
                        }
                        
                        if not dry_run:
                            # Create or update course
                            course, created = Course.objects.update_or_create(
                                code=course_code,
                                defaults=course_data
                            )
                            
                            if created:
                                created_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'Row {row_num}: Created {course_code} - {course.title}')
                                )
                            else:
                                updated_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'Row {row_num}: Updated {course_code} - {course.title}')
                                )
                        else:
                            # Dry run - just check if course exists
                            exists = Course.objects.filter(code=course_code).exists()
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
                self.stdout.write('\n' + '='*50)
                self.stdout.write(self.style.SUCCESS('IMPORT SUMMARY'))
                self.stdout.write('='*50)
                if dry_run:
                    self.stdout.write(f'Would create: {created_count} courses')
                    self.stdout.write(f'Would update: {updated_count} courses')
                else:
                    self.stdout.write(self.style.SUCCESS(f'Created: {created_count} courses'))
                    self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count} courses'))
                self.stdout.write(f'Skipped: {skipped_count} rows')
                self.stdout.write(self.style.ERROR(f'Errors: {error_count} rows'))
                self.stdout.write('='*50)
                
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
            self.stdout.write('Please make sure the file exists and the path is correct.')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading file: {str(e)}')
            )
