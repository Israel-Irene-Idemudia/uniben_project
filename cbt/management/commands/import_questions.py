import os
import csv
import re
from django.core.management.base import BaseCommand
from cbt.models import Question, Option

class Command(BaseCommand):
    help = "Import questions from a CSV file. Usage: python manage.py import_questions path/to/questions.csv"

    def add_arguments(self, parser):
        # positional optional arg (no --file)
        parser.add_argument('csv_file', nargs='?', default='questions.csv', help='Path to CSV file (default: questions.csv)')

    def handle(self, *args, **options):
        path = options['csv_file']

        # If user passed a relative path, make it relative to project CWD (where manage.py is)
        path = os.path.abspath(path)
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"CSV file not found at {path}"))
            return

        # Try to sniff delimiter / encoding if needed; we assume comma and latin1 safe fallback
        try:
            f = open(path, newline='', encoding='utf-8')
            # try reading header
            sample = f.read(2048)
            f.seek(0)
            # decide encoding later if fail
            reader = csv.DictReader(f)
        except UnicodeDecodeError:
            f = open(path, newline='', encoding='latin1')
            reader = csv.DictReader(f)

        row_count = 0
        for row in reader:
            row_count += 1
            # support various header names
            qtext = (row.get('Question') or row.get('question_text') or row.get('Question Text') or row.get('question') or '').strip()
            if not qtext:
                # skip empty lines
                continue

            # marks if present
            marks_raw = row.get('marks') or row.get('Marks') or ''
            try:
                marks = float(marks_raw) if marks_raw != '' else 1
            except Exception:
                marks = 1

            # Create question. We'll set qtype after parsing indices/options
            q = Question.objects.create(text=qtext, marks=marks)

            # Collect option columns: common header patterns
            option_keys = []
            for k in row.keys():
                if not k:
                    continue
                k_lower = k.strip().lower()
                if k_lower.startswith('option') or k_lower.startswith('option ') or re.match(r'option\s*[a-d]', k_lower) or re.match(r'option_[1-9]', k_lower) or k_lower in ('a','b','c','d'):
                    option_keys.append(k)
            # fallback explicit Option A..D
            if not option_keys:
                for key in ['Option A','Option B','Option C','Option D','option_a','option_b','option_c','option_d','A','B','C','D']:
                    if key in row:
                        option_keys.append(key)

            # Create options in the order we found them
            opts = []
            order = 1
            for key in option_keys:
                text = row.get(key) or ''
                text = text.strip()
                if text:
                    o = Option.objects.create(question=q, text=text, order=order)
                    opts.append(o)
                    order += 1

            # Determine indices field (try multiple names)
            idx_field = (row.get('indices') or row.get('correct_indices') or row.get('Answer') or row.get('answer') or row.get('correct') or '').strip()

            # Normalize index list: supports "1;2;4", "1,2", "A;C" or "A,C" or "a,c"
            indices = []
            if idx_field:
                # if looks like letters (A,B,C) convert to numbers
                # split on semicolon/comma/space
                parts = re.split(r'[;,/\s]+', idx_field)
                for p in parts:
                    p = p.strip()
                    if not p:
                        continue
                    if p.isdigit():
                        indices.append(int(p))
                    else:
                        # maybe letter like 'A' or 'c'
                        p_up = p.upper()
                        if len(p_up) == 1 and 'A' <= p_up <= 'Z':
                            # A->1, B->2
                            num = ord(p_up) - ord('A') + 1
                            indices.append(num)
                        else:
                            # try to extract digits inside parentheses or strings like "3)"
                            digits = re.findall(r'\d+', p)
                            if digits:
                                indices.append(int(digits[0]))

            # Mark the correct options based on indices
            if indices and opts:
                # set qtype based on count
                q.qtype = Question.QTYPE_MULTI if len(indices) > 1 else Question.QTYPE_MCQ
                q.save()
                for i in indices:
                    if 1 <= i <= len(opts):
                        opt = opts[i-1]  # 1-based index in CSV maps to 0-based list
                        opt.is_correct = True
                        opt.save()
            else:
                # if no indices found but options exist -> assume mcq with no answer (leave is_correct False)
                if opts:
                    q.qtype = Question.QTYPE_MCQ
                    q.save()
                else:
                    # no options => text question
                    q.qtype = Question.QTYPE_TEXT
                    q.save()

        f.close()
        self.stdout.write(self.style.SUCCESS(f"✅ Imported {row_count} rows from {path}"))
