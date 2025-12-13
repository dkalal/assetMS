from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from users.models import UserSession, AccessLog
import random
import hashlib

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample sessions and access logs for demo purposes'

    def handle(self, *args, **options):
        users = User.objects.all()
        if not users.exists():
            self.stdout.write(self.style.ERROR('No users found. Create users first.'))
            return

        # Clear existing sample data
        UserSession.objects.all().delete()
        AccessLog.objects.all().delete()

        browsers = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/91.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        
        ip_addresses = ['192.168.1.100', '10.0.0.50', '172.16.0.25', '203.0.113.10']
        
        # Create active sessions for demonstration
        session_count = 0
        for user in users:
            # Create 1-3 sessions per user
            num_sessions = random.randint(1, 3)
            
            for i in range(num_sessions):
                session_key = f'demo_session_{user.id}_{i}'
                browser = random.choice(browsers)
                ip = random.choice(ip_addresses)
                
                # Generate enhanced fingerprints
                fingerprint_data = f'{browser}|en-US|gzip, deflate|{session_key}|{timezone.now().timestamp()}'
                browser_fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
                device_fingerprint = hashlib.md5(f'{browser}|{ip}'.encode()).hexdigest()[:20]
                tab_id = f'tab_{random.randint(1000, 9999)}'
                
                # Determine session context
                context = 'admin' if user.role == 'admin' and random.random() < 0.3 else 'web'
                
                # Create session with enhanced fields
                UserSession.objects.create(
                    user=user,
                    session_key=session_key,
                    session_context=context,
                    ip_address=ip,
                    user_agent=browser,
                    browser_fingerprint=browser_fingerprint,
                    device_fingerprint=device_fingerprint,
                    tab_id=tab_id,
                    is_active=True,
                    created_at=timezone.now() - timezone.timedelta(hours=random.randint(0, 12)),
                    last_activity=timezone.now() - timezone.timedelta(minutes=random.randint(0, 60))
                )
                session_count += 1
                
                # Create login log
                AccessLog.objects.create(
                    user=user,
                    action='login',
                    ip_address=ip,
                    user_agent=browser,
                    details=f'Login from {ip}',
                    timestamp=timezone.now() - timezone.timedelta(hours=random.randint(0, 24))
                )

        # Create some failed login attempts
        for _ in range(5):
            user = random.choice(users)
            AccessLog.objects.create(
                user=user,
                action='failed_login',
                ip_address=random.choice(ip_addresses),
                user_agent=random.choice(browsers),
                details='Failed login attempt',
                timestamp=timezone.now() - timezone.timedelta(hours=random.randint(0, 24))
            )

        # Create some locked accounts (simulate)
        locked_users = random.sample(list(users), min(2, len(users)))
        for user in locked_users:
            user.account_locked_until = timezone.now() + timezone.timedelta(minutes=30)
            user.failed_login_attempts = 5
            user.save()
            
            AccessLog.objects.create(
                user=user,
                action='account_locked',
                ip_address=random.choice(ip_addresses),
                user_agent=random.choice(browsers),
                details='Account locked after 5 failed attempts',
                timestamp=timezone.now() - timezone.timedelta(minutes=random.randint(1, 30))
            )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {session_count} sessions and sample access logs')
        )