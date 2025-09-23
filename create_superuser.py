# create_superuser.py

import os
import django
from django.contrib.auth import get_user_model

# Initialize Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniben_portal.settings")
django.setup()

def run():
    User = get_user_model()
    # You can change these credentials or read from environment variables
    username = os.environ.get("SUPERUSER_NAME", "admin")
    email = os.environ.get("SUPERUSER_EMAIL", "admin@example.com")
    password = os.environ.get("SUPERUSER_PASSWORD", "admin123")

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"✅ Superuser '{username}' created successfully!")
    else:
        print(f"ℹ️ Superuser '{username}' already exists.")
