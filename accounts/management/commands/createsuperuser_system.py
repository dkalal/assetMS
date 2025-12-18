"""
Management Command: createsuperuser_system
==========================================
Purpose: Create system admin user (not tied to any company)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a system admin user (not tied to any company)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the system admin',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the system admin',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Do not prompt for input',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        noinput = options.get('noinput', False)

        if not username and not noinput:
            username = input('Username: ')
        
        if not email and not noinput:
            email = input('Email: ')

        if not username or not email:
            self.stdout.write(self.style.ERROR('Username and email are required.'))
            return

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User with username "{username}" already exists.'))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'User with email "{email}" already exists.'))
            return

        # Get password
        if noinput:
            password = 'TempPassword123!'  # Should be changed on first login
        else:
            from getpass import getpass
            password = getpass('Password: ')
            password_confirm = getpass('Password (again): ')
            
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match.'))
                return

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_system_admin=True,
                    company=None,  # System admin has no company
                    is_staff=True,
                    is_superuser=True,
                    email_verified=True,
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'System admin user "{username}" created successfully.\n'
                        f'User ID: {user.id}\n'
                        f'Email: {user.email}\n'
                        f'System Admin: {user.is_system_admin}'
                    )
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating system admin: {e}'))








