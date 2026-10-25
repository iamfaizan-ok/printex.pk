import os
import secrets
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class Command(BaseCommand):
    help = "Creates or updates an initial administrator account for PrintX. Requires strong password."

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='Administrator username')
        parser.add_argument('--email', type=str, required=True, help='Administrator email address')
        parser.add_argument('--password', type=str, required=False, default=None, help='Administrator password (min 8 chars)')

    def handle(self, *args, **options):
        username = options['username'].strip()
        email = options['email'].strip().lower()
        password = options.get('password') or os.getenv('PRINTX_ADMIN_INITIAL_PASSWORD')

        if not password:
            raise CommandError(
                "A secure password must be provided via the --password flag or the PRINTX_ADMIN_INITIAL_PASSWORD environment variable."
            )

        try:
            validate_password(password)
        except ValidationError as err:
            raise CommandError(f"Password validation failed: {'; '.join(err.messages)}")

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.email = email
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        action = "Created new" if created else "Updated existing"
        self.stdout.write(self.style.SUCCESS(f"{action} administrator account '{username}' successfully (is_staff=True, is_superuser=True)."))
