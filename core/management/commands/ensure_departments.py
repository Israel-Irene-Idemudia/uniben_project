import csv
from django.core.management.base import BaseCommand
from core.models import Department, Faculty

class Command(BaseCommand):
    help = 'Create missing Faculties and Departments from CSV'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='import_data/latest version.csv')

    def handle(self, *args, **options):
        file_path = options['file']
        
        created_fac = 0
        created_dept = 0

        try:
            # use utf-8-sig to handle BOM if present
            with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    # 1. Get Names
                    faculty_name = row.get('faculty_title', '').strip()
                    faculty_code = row.get('faculty_code', '').strip()[:10]
                    
                    dept_name = row.get('department_title', '').strip()
                    dept_code = row.get('department_code', '').strip()[:10]

                    if not faculty_name or not dept_name:
                        continue

                    # 2. Ensure Faculty Exists
                    faculty, f_created = Faculty.objects.get_or_create(
                        name__iexact=faculty_name,
                        defaults={
                            'name': faculty_name,
                            'code': faculty_code
                        }
                    )
                    if f_created:
                        self.stdout.write(self.style.SUCCESS(f"Created Faculty: {faculty_name}"))
                        created_fac += 1

                    # 3. Ensure Department Exists (Linked to Faculty)
                    department, d_created = Department.objects.get_or_create(
                        name__iexact=dept_name,
                        defaults={
                            'name': dept_name,
                            'code': dept_code,
                            'faculty': faculty
                        }
                    )
                    
                    # Update faculty if department exists but has no faculty
                    if not d_created and department.faculty != faculty:
                        department.faculty = faculty
                        department.save()
                        self.stdout.write(f"Updated Faculty for: {dept_name}")

                    if d_created:
                        self.stdout.write(self.style.SUCCESS(f"Created Dept: {dept_name}"))
                        created_dept += 1

            self.stdout.write(self.style.SUCCESS(f"\nDone! Created {created_fac} Faculties and {created_dept} Departments."))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))