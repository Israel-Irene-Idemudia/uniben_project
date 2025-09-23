import os
import django
import pandas as pd
from django.db import transaction

# ---------------- Django setup ----------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniben_portal.settings")
django.setup()

from cbt.models import Exam, Question, Option, ExamQuestion
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

    for filename in os.listdir(CSV_FOLDER):
        if not filename.endswith(".csv"):
            continue

        csv_path = os.path.join(CSV_FOLDER, filename)
        try:
            df = pd.read_csv(
                csv_path,
                quotechar='"',
                skipinitialspace=True,
                on_bad_lines='skip'  # skip malformed rows
            )
        except Exception as e:
            print(f"❌ Failed to read {filename}: {e}")
            continue

        df.columns = df.columns.str.strip()  # remove extra spaces

        required_cols = ["Question", "Option A", "Option B"]
        for col in required_cols:
            if col not in df.columns:
                print(f"❌ Skipping {filename}: missing required column '{col}'")
                continue

        # Create a default exam per CSV file
        exam_title = os.path.splitext(filename)[0]
        exam, _ = Exam.objects.get_or_create(
            title=exam_title,
            course=None,
            defaults={"created_by": superuser}
        )

        print(f"📄 Processing {filename} ({len(df)} questions)")

        for _, row in df.iterrows():
            # Skip rows missing question text
            if pd.isna(row["Question"]):
                continue

            question = Question.objects.create(
                text=row["Question"],
                qtype="mcq",
                marks=1,
                created_by=superuser
            )

            # Link question to exam
            order = exam.exam_questions.count() + 1
            ExamQuestion.objects.create(exam=exam, question=question, order=order)

            # Options
            correct_raw = str(row.get("correct_indices", "")).replace(" ", "")
            correct_indices = [int(x) for x in correct_raw.split(",") if x.isdigit()]

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
