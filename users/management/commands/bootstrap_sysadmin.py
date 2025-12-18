import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Bootstrap a global system admin (is_system_admin=True, company=None). Safe to run multiple times."

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email address for the system admin (also used as username if username not provided)')
        parser.add_argument('--username', type=str, help='Username for the system admin (defaults to email)')
        parser.add_argument('--password', type=str, help='Password for the system admin (can also come from env SYSADMIN_PASSWORD)')
        parser.add_argument('--first_name', type=str, default='', help='First name')
        parser.add_argument('--last_name', type=str, default='', help='Last name')
        parser.add_argument('--superuser', action='store_true', help='Also mark as Django superuser (default: true)')
        parser.add_argument('--no-superuser', action='store_true', help='Do not mark as superuser')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options.get('email') or os.getenv('SYSADMIN_EMAIL')
        username = options.get('username') or email or os.getenv('SYSADMIN_USERNAME')
        password = options.get('password') or os.getenv('SYSADMIN_PASSWORD')
        first_name = options.get('first_name') or os.getenv('SYSADMIN_FIRST_NAME', '')
        last_name = options.get('last_name') or os.getenv('SYSADMIN_LAST_NAME', '')

        if not email or not password:
            raise CommandError('email and password are required (provide via args or ENV: SYSADMIN_EMAIL, SYSADMIN_PASSWORD)')
        if not username:
            username = email

        mark_superuser = True
        if options.get('no-superuser'):
            mark_superuser = False
        if options.get('superuser'):
            mark_superuser = True

        user, created = User.objects.get_or_create(username=username, defaults={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
        })

        # Make sure flags are set
        user.email = email
        user.is_active = True
        user.is_staff = True  # allow Django admin login
        user.is_system_admin = True
        if mark_superuser:
            user.is_superuser = True
        # Global operator must not belong to any company
        user.company = None
        if created:
            user.set_password(password)
        else:
            # Only reset password if SYSADMIN_RESET=1
            if os.getenv('SYSADMIN_RESET') == '1':
                user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"System admin ready: username={user.username}, email={user.email}, is_superuser={user.is_superuser}, is_system_admin={user.is_system_admin}"
        ))
