import os
import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Course
from cbt.models import Exam, Question, Option

User = get_user_model()
DEFAULT_USER_ID = 1  # change to a valid admin user ID
DEFAULT_FOLDER = 'import_questions/'  # default folder with CSVs

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
            try:
                course = Course.objects.get(code=course_code)
            except Course.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Course {course_code} does not exist, skipping'))
                continue

            # Create or reuse exam
            exam, created = Exam.objects.get_or_create(
                title=f"{course.code} Exam",
                course=course,
                defaults={'created_by': user}
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created exam for {course.code}'))
            else:
                self.stdout.write(self.style.WARNING(f'Using existing exam for {course.code}'))

            # Open CSV and normalize headers
            file_path = os.path.join(CSV_DIR, filename)
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if reader.fieldnames is None:
                    self.stdout.write(self.style.WARNING(f'No headers found in {filename}, skipping'))
                    continue

                # ✅ Normalize headers safely
                reader.fieldnames = [
                    str(h).strip().lower() if h else '' for h in reader.fieldnames
                ]

                for row in reader:
                    # ✅ Normalize row safely
                    row = {
                        (str(k).strip().lower() if k else ''): (str(v).strip() if v else '')
                        for k, v in row.items()
                    }

                    # Flexible column names
                    question_text = row.get('question') or row.get('text')
                    if not question_text:
                        self.stdout.write(self.style.WARNING(f'Skipping row with no question text in {filename}'))
                        continue

                    # ✅ Safe handling for correct_index
                    correct_index = row.get('correct_indices')
                    if not correct_index:
                        correct_index = row.get('correct')
                    if not correct_index:
                        correct_index = 'A'
                    correct_index = str(correct_index).strip().upper()

                    # 🔹 Check if question already exists in this exam
                    existing_question = (
                        Question.objects.filter(text=question_text, examquestion__exam=exam).first()
                    )

                    if existing_question:
                        question = existing_question
                        self.stdout.write(self.style.NOTICE(f'Updating existing question: "{question_text[:50]}..."'))
                        # Delete old options (to avoid duplicates) and recreate
                        question.options.all().delete()
                    else:
                        question = Question.objects.create(
                            text=question_text,
                            qtype=Question.QTYPE_MCQ,
                            created_by=user
                        )
                        exam.exam_questions.create(question=question)
                        self.stdout.write(self.style.SUCCESS(f'Created new question: "{question_text[:50]}..."'))

                    # Create options A-D
                    for opt_label in ['A', 'B', 'C', 'D']:
                        col_name = f'option_{opt_label.lower()}'
                        option_text = row.get(col_name)
                        if not option_text:
                            continue

                        is_correct = (opt_label == correct_index)
                        Option.objects.create(
                            question=question,
                            text=option_text,
                            is_correct=is_correct,
                            order=ord(opt_label)
                        )

            self.stdout.write(self.style.SUCCESS(f'Imported/updated questions from {filename}'))
