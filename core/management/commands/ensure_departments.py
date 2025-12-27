import csv
from django.core.management.base import BaseCommand
from core.models import Department, Faculty

class Command(BaseCommand):
    help = 'Create missing Faculties and Departments from CSV safely'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='import_data/latest version.csv')

    def handle(self, *args, **options):
        file_path = options['file']
        
        created_fac = 0
        created_dept = 0

        try:
            # Use utf-8-sig to handle potential BOM characters from Excel
            with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    # 1. Get Names and Strip Whitespace
                    faculty_name = row.get('faculty_title', '').strip()
                    dept_name = row.get('department_title', '').strip()

                    # Check if 'code' columns exist in CSV, but don't assume models have them
                    faculty_code = row.get('faculty_code', '').strip()[:10]
                    dept_code = row.get('department_code', '').strip()[:10]

                    if not faculty_name or not dept_name:
                        continue

                    # 2. Ensure Faculty Exists
                    # We check if the Faculty model actually has a 'code' field
                    faculty_defaults = {'name': faculty_name}
                    
                    if hasattr(Faculty, 'code'):
                         faculty_defaults['code'] = faculty_code

                    faculty, f_created = Faculty.objects.get_or_create(
                        name__iexact=faculty_name,
                        defaults=faculty_defaults
                    )
                    
                    if f_created:
                        self.stdout.write(self.style.SUCCESS(f"Created Faculty: {faculty_name}"))
                        created_fac += 1

                    # 3. Ensure Department Exists (Linked to Faculty)
                    dept_defaults = {
                        'name': dept_name,
                        'faculty': faculty
                    }
                    
                    if hasattr(Department, 'code'):
                         dept_defaults['code'] = dept_code

                    department, d_created = Department.objects.get_or_create(
                        name__iexact=dept_name,
                        defaults=dept_defaults
                    )
                    
                    # Fix: If department exists but has NO faculty or WRONG faculty, update it
                    if not d_created and department.faculty != faculty:
                        department.faculty = faculty
                        department.save()
                        self.stdout.write(f"Updated Faculty linkage for: {dept_name}")

                    if d_created:
                        self.stdout.write(self.style.SUCCESS(f"Created Dept: {dept_name}"))
                        created_dept += 1

            self.stdout.write(self.style.SUCCESS(f"\nDone! Created {created_fac} Faculties and {created_dept} Departments."))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))