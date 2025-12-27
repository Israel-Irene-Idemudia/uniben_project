"""
Cleanup script to remove incorrectly imported data from the bad import.
This will:
- Delete all Courses that were created during the import
- Delete all Levels that were created during the import
- Delete all CourseAreas that were created during the import

Run with: python manage.py cleanup_bad_import
Add --confirm to actually delete
"""

from django.core.management.base import BaseCommand
from core.models import Course, Level, CourseArea


class Command(BaseCommand):
    help = 'Clean up incorrectly imported courses, levels, and course areas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete the data (without this flag, just shows what would be deleted)'
        )
        parser.add_argument(
            '--keep-course-areas',
            action='store_true',
            help='Keep course areas, only delete courses and levels'
        )

    def handle(self, *args, **options):
        confirm = options['confirm']
        keep_areas = options['keep_course_areas']

        if not confirm:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - Add --confirm to actually delete'))
            self.stdout.write('')

        # Count and delete courses
        course_count = Course.objects.count()
        self.stdout.write(f'Courses to delete: {course_count}')
        
        if confirm and course_count > 0:
            Course.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {course_count} courses'))

        # Count and delete levels
        level_count = Level.objects.count()
        self.stdout.write(f'Levels to delete: {level_count}')
        
        if confirm and level_count > 0:
            Level.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {level_count} levels'))

        # Count and optionally delete course areas
        if not keep_areas:
            area_count = CourseArea.objects.count()
            self.stdout.write(f'CourseAreas to delete: {area_count}')
            
            if confirm and area_count > 0:
                CourseArea.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'Deleted {area_count} course areas'))
        else:
            self.stdout.write('Keeping course areas (--keep-course-areas flag set)')

        self.stdout.write('')
        if confirm:
            self.stdout.write(self.style.SUCCESS('Cleanup complete!'))
        else:
            self.stdout.write(self.style.WARNING('Run with --confirm to actually delete this data'))
