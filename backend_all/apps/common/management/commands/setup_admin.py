import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Creates or resets an initial admin staff account for the PrintX Admin Portal."

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Admin username')
        parser.add_argument('--email', type=str, default='admin@printx.pk', help='Admin email')
        parser.add_argument('--password', type=str, default='Admin@PrintX2026!', help='Admin password')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = os.getenv('PRINTX_ADMIN_INITIAL_PASSWORD', options['password'])

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.email = email
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        action = "Created new" if created else "Updated existing"
        self.stdout.write(self.style.SUCCESS(f"{action} admin account '{username}' successfully (is_staff=True, is_superuser=True)."))
