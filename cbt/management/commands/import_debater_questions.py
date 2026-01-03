import json
from django.core.management.base import BaseCommand
from cbt.models import DebaterQuestion


class Command(BaseCommand):
    help = 'Import demo Debater questions from JSON file'

    def handle(self, *args, **options):
        # Path to the JSON file in backend fixtures
        import os
        from django.conf import settings
        
        json_path = os.path.join(settings.BASE_DIR, 'cbt', 'fixtures', 'debater_questions.json')
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            imported_count = 0
            skipped_count = 0
            
            for item in data:
                statement = item.get('statement')
                answer = item.get('answer')
                category = item.get('category')
                
                # Check if question already exists
                if DebaterQuestion.objects.filter(statement=statement).exists():
                    skipped_count += 1
                    continue
                
                # Create new question
                DebaterQuestion.objects.create(
                    statement=statement,
                    answer=answer,
                    category=category,
                    is_active=True
                )
                imported_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported {imported_count} questions. '
                    f'Skipped {skipped_count} duplicates.'
                )
            )
            
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'File not found: {json_path}')
            )
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR(f'Invalid JSON in file: {json_path}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error importing questions: {str(e)}')
            )
