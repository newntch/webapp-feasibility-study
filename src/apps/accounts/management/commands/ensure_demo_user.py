from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create the configured local demo account when demo access is enabled."

    def handle(self, *args, **options):
        if not settings.DEMO_ACCOUNT_ENABLED:
            self.stdout.write("Demo account provisioning is disabled.")
            return

        email = settings.DEMO_ACCOUNT_EMAIL.strip().lower()
        password = settings.DEMO_ACCOUNT_PASSWORD
        if not email or not password:
            raise CommandError("DEMO_ACCOUNT_EMAIL and DEMO_ACCOUNT_PASSWORD are required.")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "id": "demo-researcher",
                "name": "Demo Researcher",
                "role": "researcher",
                "provider": "credentials",
                "is_active": True,
                "password": make_password(password),
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created demo account {user.email}."))
        else:
            self.stdout.write(f"Demo account {user.email} already exists.")
