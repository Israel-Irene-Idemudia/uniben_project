import os
import sys
import subprocess
import django
import pandas as pd

# ---------------- CONFIG ----------------
DB_NAME = "uniben_db"
CSV_PATH = "import_data/courses part 1.csv"  # path to your CSV

# Django superuser info
DJANGO_SUPERUSER = os.environ.get("SUPERUSER_NAME", "problem_solvers")
DJANGO_EMAIL = os.environ.get("SUPERUSER_EMAIL", "admin@example.com")
DJANGO_PASSWORD = os.environ.get("SUPERUSER_PASSWORD", "problemsolvers")

# List all apps that have migrations
APPS_TO_MIGRATE = ["core", "cbt"]  # add all apps here

# ---------------- Initialize Django ----------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniben_portal.settings")
django.setup()

# ---------------- Clear migrations ----------------
def clear_migrations():
    for app in APPS_TO_MIGRATE:
        path = os.path.join(app, "migrations")
        if not os.path.exists(path):
            continue
        for f in os.listdir(path):
            if f.endswith(".py") and f != "__init__.py":
                os.remove(os.path.join(path, f))
        print(f"✅ Cleared migrations for {app}")

# ---------------- Rebuild migrations ----------------
def make_migrations():
    try:
        for app in APPS_TO_MIGRATE:
            subprocess.run(f"python manage.py makemigrations {app}", shell=True, check=True)
        print("✅ Migrations created successfully.")
    except subprocess.CalledProcessError as e:
        print("❌ Failed to create migrations:", e)
        sys.exit(1)

def migrate():
    try:
        subprocess.run("python manage.py migrate", shell=True, check=True)
        print("✅ Migrations applied successfully.")
    except subprocess.CalledProcessError as e:
        print("❌ Failed to apply migrations:", e)
        sys.exit(1)

# ---------------- Load CSV ----------------
from core.models import Course, Level, Department, Faculty, CourseArea

def load_csv():
    try:
        df = pd.read_csv(CSV_PATH)

        for _, row in df.iterrows():
            # 1️⃣ Get or create Faculty
            faculty_obj, _ = Faculty.objects.get_or_create(name=row["Faculty"])

            # 2️⃣ Get or create Department
            dept_obj, _ = Department.objects.get_or_create(
                name=row["Department"],
                faculty=faculty_obj
            )

            # 3️⃣ Optional: CourseArea
            course_area_name = row.get("Course Area")
            if course_area_name and not pd.isna(course_area_name):
                course_area_obj, _ = CourseArea.objects.get_or_create(
                    name=course_area_name,
                    department=dept_obj
                )
            else:
                course_area_obj = None

            # 4️⃣ Get or create Level
            level_obj, _ = Level.objects.get_or_create(
                name=row["Level"],
                department=dept_obj,
                course_area=course_area_obj
            )

            # 5️⃣ Create Course
            Course.objects.create(
                code=row["Course Code"],
                title=row["Course Title"],
                level=level_obj
            )

        print(f"✅ Loaded {len(df)} courses from CSV successfully!")
    except KeyError as e:
        print(f"❌ CSV column missing: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to load CSV: {e}")
        sys.exit(1)

# ---------------- Create Django superuser ----------------
def create_superuser():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(username=DJANGO_SUPERUSER).exists():
        User.objects.create_superuser(DJANGO_SUPERUSER, DJANGO_EMAIL, DJANGO_PASSWORD)
        print(f"✅ Django superuser '{DJANGO_SUPERUSER}' created!")
    else:
        print(f"ℹ️ Superuser '{DJANGO_SUPERUSER}' already exists.")

# ---------------- RUN ----------------
if __name__ == "__main__":
    clear_migrations()
    print("ℹ️ Skipping database reset step. Make sure database exists and credentials are correct.")
    make_migrations()
    migrate()
    load_csv()
    create_superuser()
    print("🎉 Project reset and CSV loaded successfully!")
