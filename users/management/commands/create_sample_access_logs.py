from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from users.models import AccessLog, UserSession
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample access logs for demo purposes'

    def handle(self, *args, **options):
        users = User.objects.all()
        if not users.exists():
            self.stdout.write(self.style.ERROR('No users found. Create users first.'))
            return

        actions = ['login', 'logout', 'failed_login', 'password_change']
        ip_addresses = ['192.168.1.100', '10.0.0.50', '172.16.0.25', '203.0.113.10']
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]

        # Create sample access logs
        for i in range(20):
            user = random.choice(users)
            action = random.choice(actions)
            
            AccessLog.objects.create(
                user=user,
                action=action,
                ip_address=random.choice(ip_addresses),
                user_agent=random.choice(user_agents),
                details=f'Sample {action} event for demo'
            )

        # Create sample user sessions
        for user in users[:3]:  # Only for first 3 users
            UserSession.objects.create(
                user=user,
                session_key=f'demo_session_{user.id}',
                ip_address=random.choice(ip_addresses),
                user_agent=random.choice(user_agents),
                is_active=True
            )

        self.stdout.write(
            self.style.SUCCESS('Successfully created sample access logs and sessions')
        )