from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserSession, AccessLog
import logging
import hashlib

User = get_user_model()
logger = logging.getLogger(__name__)

class EnterpriseSessionMiddleware(MiddlewareMixin):
    """
    Enterprise Multi-Session Tracking Middleware
    Supports multiple concurrent sessions per user
    """
    
    def process_request(self, request):
        """Track session activity with context isolation"""
        if request.user.is_authenticated:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            browser_fingerprint = self.generate_browser_fingerprint(request)
            session_context = self.detect_session_context(request)
            
            # Update or create user session with context
            user_session, created = UserSession.objects.get_or_create(
                user=request.user,
                session_key=session_key,
                browser_fingerprint=browser_fingerprint,
                session_context=session_context,
                defaults={
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'is_active': True
                }
            )
            
            if not created:
                user_session.last_activity = timezone.now()
                user_session.is_active = True
                user_session.save(update_fields=['last_activity', 'is_active'])
            
            # Update user's last activity
            User.objects.filter(id=request.user.id).update(last_activity=timezone.now())
            
            # Store session info in request
            request.user_session = user_session
            
            # Enterprise security: Check context access permissions
            if not self.check_context_permissions(request.user, session_context, request):
                from django.contrib.auth import logout
                logout(request)
                return
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
    
    def generate_browser_fingerprint(self, request):
        """Generate browser fingerprint for session identification"""
        fingerprint_data = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
            str(request.session.session_key or '')
        ]
        
        fingerprint_string = '|'.join(fingerprint_data)
        return hashlib.md5(fingerprint_string.encode()).hexdigest()[:20]
    
    def detect_session_context(self, request):
        """Detect session context based on URL patterns"""
        path = request.path
        
        if path.startswith('/admin/'):
            return 'admin'
        elif path.startswith('/api/'):
            return 'api'
        elif 'mobile' in request.META.get('HTTP_USER_AGENT', '').lower():
            return 'mobile'
        else:
            return 'web'
    
    def check_context_permissions(self, user, context, request):
        """Enterprise context access control"""
        # Admin context requires superuser or admin role
        if context == 'admin':
            if not (user.is_superuser or user.role == 'admin'):
                logger.warning(f'Non-admin user {user.username} attempted admin access from {self.get_client_ip(request)}')
                return False
        
        # API context requires specific permissions
        elif context == 'api':
            if not user.is_active:
                return False
        
        return True

class SessionCleanupMiddleware(MiddlewareMixin):
    """
    Cleanup expired sessions periodically
    Enterprise pattern: Background cleanup tasks
    """
    
    def process_response(self, request, response):
        """Cleanup expired sessions on every 100th request"""
        import random
        if random.randint(1, 100) == 1:  # 1% chance
            self.cleanup_expired_sessions()
        return response
    
    def cleanup_expired_sessions(self):
        """Remove sessions older than 24 hours of inactivity"""
        try:
            cutoff_time = timezone.now() - timezone.timedelta(hours=24)
            expired_count = UserSession.objects.filter(
                last_activity__lt=cutoff_time
            ).update(is_active=False, logout_reason='timeout')
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")

class LoginLogoutMiddleware(MiddlewareMixin):
    """
    Track login/logout events for audit trail
    Enterprise pattern: Comprehensive audit logging
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Track login/logout events"""
        if hasattr(request, 'resolver_match') and request.resolver_match:
            url_name = request.resolver_match.url_name
            
            # Track logout events  
            if url_name == 'logout' and request.user.is_authenticated:
                self.track_logout(request)
    
    def track_logout(self, request):
        """Track logout events"""
        try:
            AccessLog.objects.create(
                user=request.user,
                action='logout',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details=f'User logged out from session'
            )
            
            # Mark current session as inactive
            if hasattr(request, 'user_session'):
                request.user_session.is_active = False
                request.user_session.logout_reason = 'manual'
                request.user_session.save()
                
        except Exception as e:
            logger.error(f"Logout tracking error: {e}")
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip