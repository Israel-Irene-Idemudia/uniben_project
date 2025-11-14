
import os
import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Course
from cbt.models import Exam, Question, Option

User = get_user_model()
DEFAULT_USER_ID = 1
DEFAULT_FOLDER = 'import_questions/'

class Command(BaseCommand):
    help = 'Import multiple CSV files for CBT exams'

    def add_arguments(self, parser):
        parser.add_argument(
            '--folder',
            type=str,
            default=DEFAULT_FOLDER,
            help='Folder containing course CSVs'
        )

    def handle(self, *args, **options):
        CSV_DIR = options['folder']

        if not os.path.exists(CSV_DIR):
            self.stdout.write(self.style.ERROR(f'Folder {CSV_DIR} does not exist'))
            return

        try:
            user = User.objects.get(id=DEFAULT_USER_ID)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with id {DEFAULT_USER_ID} does not exist'))
            return

        for filename in os.listdir(CSV_DIR):
            if not filename.endswith('.csv'):
                continue

            course_code = filename.replace('.csv', '').strip()
            
            # --- FIX: Use filter().first() to handle duplicate courses ---
            course = Course.objects.filter(code=course_code).first()
            if not course:
                self.stdout.write(self.style.WARNING(f'Course {course_code} does not exist, skipping'))
                continue
            # --- END FIX ---

            exam, created = Exam.objects.get_or_create(
                title=f"{course.code} Exam",
                course=course,
                defaults={'created_by': user}
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created exam for {course.code}'))
            else:
                self.stdout.write(self.style.WARNING(f'Using existing exam for {course.code}'))

            file_path = os.path.join(CSV_DIR, filename)
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if reader.fieldnames is None:
                    self.stdout.write(self.style.WARNING(f'No headers found in {filename}, skipping'))
                    continue

                reader.fieldnames = [str(h).strip().lower() if h else '' for h in reader.fieldnames]

                for row in reader:
                    row = {
                        (str(k).strip().lower() if k else ''): (str(v).strip() if v else '')
                        for k, v in row.items()
                    }

                    question_text = row.get('question') or row.get('text')
                    if not question_text:
                        self.stdout.write(self.style.WARNING(f'Skipping row with no question text in {filename}'))
                        continue

                    correct_index_raw = row.get('correct_indices') or row.get('correct')
                    correct_index_val = str(correct_index_raw).strip().upper() if correct_index_raw else ''
                    
                    correct_label = ''
                    if correct_index_val == '-1':
                        pass # No correct answer
                    elif correct_index_val:
                        try:
                            numeric_index = int(correct_index_val)
                            if 0 <= numeric_index <= 4: # 0-based A-E
                                correct_label = chr(ord('A') + numeric_index)
                            elif 1 <= numeric_index <= 5: # 1-based A-E
                                correct_label = chr(ord('A') + numeric_index - 1)
                        except (ValueError, TypeError):
                            if correct_index_val in ['A', 'B', 'C', 'D', 'E']:
                                correct_label = correct_index_val

                    existing_question = (
                        Question.objects.filter(text=question_text, examquestion__exam=exam).first()
                    )

                    if existing_question:
                        question = existing_question
                        question.options.all().delete()
                    else:
                        question = Question.objects.create(
                            text=question_text,
                            qtype=Question.QTYPE_MCQ,
                            created_by=user
                        )
                        exam.exam_questions.create(question=question)

                    for opt_label in ['A', 'B', 'C', 'D', 'E']:
                        col_name_1 = f'option_{opt_label.lower()}'
                        col_name_2 = f'option {opt_label.lower()}'
                        option_text = row.get(col_name_1) or row.get(col_name_2)
                        
                        if not option_text:
                            continue

                        is_correct = (opt_label == correct_label)
                        Option.objects.create(
                            question=question,
                            text=option_text,
                            is_correct=is_correct,
                            order=ord(opt_label)
                        )

            self.stdout.write(self.style.SUCCESS(f'Imported/updated questions from {filename}'))
