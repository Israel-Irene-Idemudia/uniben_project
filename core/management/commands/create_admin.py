from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create a default superuser if it doesn’t exist"

    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(username="problem_solvers").exists():
            User.objects.create_superuser(
                username="problem_solvers",
                email="admin@example.com",
                password="problemsolvers"
            )
            self.stdout.write(self.style.SUCCESS("✅ Superuser created"))
        else:
            self.stdout.write(self.style.WARNING("⚠️ Superuser already exists"))
