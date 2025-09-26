#!/usr/bin/env bash
# exit on error
set -o errexit  

# 1. Install dependencies
pip install -r requirements.txt

# 2. Apply database migrations
python3 manage.py migrate --noinput

# 3. Load initial data (Faculties, Departments, Levels, Course Areas, Courses)
if [ -f "initial_data.json" ]; then
    echo "📥 Loading initial data from initial_data.json..."
    python3 manage.py loaddata initial_data.json || true
else
    echo "⚠️ No initial_data.json found, skipping loaddata step."
fi

# 3b. Load CBT questions if the fixture exists
if [ -f "cbt_questions.json" ]; then
    echo "📥 Loading CBT questions from cbt_questions.json..."
    python3 manage.py loaddata cbt_questions.json || true
else
    echo "⚠️ No cbt_questions.json found, skipping CBT data load."
fi

# 4. Collect static files
python3 manage.py collectstatic --noinput

# 5. (Optional) Run your own script for superuser creation
python3 manage.py shell -c "import create_superuser; create_superuser.run()" || true

