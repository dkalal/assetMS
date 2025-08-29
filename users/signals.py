from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AccessLog, UserSession
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """Track successful login events"""
    try:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create access log
        AccessLog.objects.create(
            user=user,
            action='login',
            ip_address=ip_address,
            user_agent=user_agent,
            details=f'Successful login from {ip_address}'
        )
        
        # Reset failed login attempts
        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.save(update_fields=['failed_login_attempts'])
            
        logger.info(f"User {user.username} logged in from {ip_address}")
        
    except Exception as e:
        logger.error(f"Login tracking error: {e}")

@receiver(user_logged_out)
def track_user_logout(sender, request, user, **kwargs):
    """Track logout events"""
    try:
        if user:
            ip_address = get_client_ip(request)
            
            # Create access log
            AccessLog.objects.create(
                user=user,
                action='logout',
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details=f'User logged out from {ip_address}'
            )
            
            # Deactivate user sessions
            UserSession.objects.filter(
                user=user,
                session_key=request.session.session_key
            ).update(is_active=False)
            
            logger.info(f"User {user.username} logged out from {ip_address}")
            
    except Exception as e:
        logger.error(f"Logout tracking error: {e}")

@receiver(user_login_failed)
def track_failed_login(sender, credentials, request, **kwargs):
    """Track failed login attempts for security monitoring"""
    try:
        username = credentials.get('username', '')
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Try to find user and increment failed attempts
        try:
            user = User.objects.get(username=username)
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                from django.utils import timezone
                user.account_locked_until = timezone.now() + timezone.timedelta(minutes=30)
                
                # Create lock log
                AccessLog.objects.create(
                    user=user,
                    action='account_locked',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details=f'Account locked after {user.failed_login_attempts} failed attempts'
                )
                
            user.save()
            
        except User.DoesNotExist:
            user = None
        
        # Create failed login log
        AccessLog.objects.create(
            user=user,
            action='failed_login',
            ip_address=ip_address,
            user_agent=user_agent,
            details=f'Failed login attempt for username: {username}'
        )
        
        logger.warning(f"Failed login attempt for {username} from {ip_address}")
        
    except Exception as e:
        logger.error(f"Failed login tracking error: {e}")

def get_client_ip(request):
    """Get real client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip