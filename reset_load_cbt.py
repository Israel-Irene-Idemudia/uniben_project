import os
import django
import pandas as pd
from django.db import transaction

# ---------------- Django setup ----------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniben_portal.settings")
django.setup()

from cbt.models import Exam, Question, Option, ExamQuestion
from django.apps import apps
Course = apps.get_model('course', 'Course')
from django.contrib.auth import get_user_model

User = get_user_model()
superuser = User.objects.first()  # Or specify a user for created_by

# ---------------- Config ----------------
CSV_FOLDER = "import_questions"  # folder containing all CSVs

# ---------------- Clear existing CBT data ----------------
def clear_cbt_data():
    print("⚠️ Clearing previous CBT data...")
    Option.objects.all().delete()
    ExamQuestion.objects.all().delete()
    Question.objects.all().delete()
    Exam.objects.all().delete()
    print("✅ Previous CBT data cleared.\n")

# ---------------- Load all CSVs ----------------
def load_cbts():
    clear_cbt_data()

    all_courses = list(Course.objects.all())

    for filename in os.listdir(CSV_FOLDER):
        if not filename.endswith(".csv"):
            continue

        csv_path = os.path.join(CSV_FOLDER, filename)
        try:
            df = pd.read_csv(
                csv_path,
                quotechar='"',
                skipinitialspace=True,
                on_bad_lines='skip'
            )
        except Exception as e:
            print(f"❌ Failed to read {filename}: {e}")
            continue

        df.columns = df.columns.str.strip()

        required_cols = ["Question", "Option A", "Option B"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"❌ Skipping {filename}: missing required columns {missing_cols}")
            continue

        exam_title = os.path.splitext(filename)[0]
        normalized_exam_title = exam_title.replace(" ", "").upper()

        course_found = None
        for course_obj in all_courses:
            normalized_course_code = course_obj.code.replace(" ", "").upper()
            if normalized_course_code == normalized_exam_title:
                course_found = course_obj
                break

        if not course_found:
            print(f"⚠️ Skipping {filename}: Course with code '{exam_title}' not found.")
            continue
        
        course = course_found

        exam, _ = Exam.objects.get_or_create(
            title=exam_title,
            course=course,
            defaults={"created_by": superuser}
        )

        print(f"📄 Processing {filename} ({len(df)} questions)")

        for _, row in df.iterrows():
            if pd.isna(row["Question"]):
                continue

            question = Question.objects.create(
                text=row["Question"],
                qtype="mcq",
                marks=1,
                created_by=superuser
            )

            order = exam.exam_questions.count() + 1
            ExamQuestion.objects.create(exam=exam, question=question, order=order)

            correct_raw = str(row.get("correct_indices", "")).replace(" ", "")
            correct_indices = []
            if correct_raw:
                try:
                    correct_indices = [int(x) for x in correct_raw.split(",") if x.isdigit()]
                except (ValueError, TypeError):
                    pass

            for idx, col in enumerate(["Option A", "Option B", "Option C", "Option D", "Option E"], start=1):
                text = row.get(col)
                if pd.isna(text) or not text:
                    continue
                Option.objects.create(
                    question=question,
                    text=text,
                    is_correct=(idx in correct_indices),
                    order=idx
                )

        print(f"✅ Finished loading {filename}\n")


if __name__ == "__main__":
    with transaction.atomic():
        load_cbts()
    print("🎉 All CBT CSVs loaded successfully!")