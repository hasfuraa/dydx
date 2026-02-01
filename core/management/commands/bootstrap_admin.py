from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
import os


class Command(BaseCommand):
    help = "Create an initial admin user if none exists."

    def handle(self, *args, **options):
        email = os.getenv("ADMIN_EMAIL")
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD")

        if not email or not password:
            self.stdout.write("ADMIN_EMAIL or ADMIN_PASSWORD not set; skipping bootstrap.")
            return

        user_model = get_user_model()
        if user_model.objects.filter(is_staff=True).exists():
            self.stdout.write("Admin user already exists; skipping bootstrap.")
            return

        user = user_model.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(f"Created admin user {user.username} ({user.email}).")
