from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from .models import UserSession, AccessLog
import logging
import hashlib
import uuid

User = get_user_model()
logger = logging.getLogger(__name__)

class EnterpriseConcurrentSessionMiddleware(MiddlewareMixin):
    """
    Enterprise Concurrent Session Management Middleware
    Handles multiple simultaneous sessions per user across different tabs/browsers
    """
    
    def process_request(self, request):
        """Process incoming request with concurrent session support"""
        if not request.user.is_authenticated:
            return None
            
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        # Generate comprehensive fingerprints
        browser_fingerprint = self.generate_browser_fingerprint(request)
        device_fingerprint = self.generate_device_fingerprint(request)
        tab_id = self.get_or_create_tab_id(request)
        
        # Detect session context
        session_context = self.detect_session_context(request)
        
        # Get client information
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        try:
            with transaction.atomic():
                # Find or create session with comprehensive matching
                user_session = self.get_or_create_session(
                    user=request.user,
                    session_key=session_key,
                    browser_fingerprint=browser_fingerprint,
                    device_fingerprint=device_fingerprint,
                    tab_id=tab_id,
                    session_context=session_context,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Update session activity
                user_session.last_activity = timezone.now()
                user_session.is_active = True
                user_session.save(update_fields=['last_activity', 'is_active'])
                
                # Update user's last activity
                User.objects.filter(id=request.user.id).update(last_activity=timezone.now())
                
                # Store session info in request
                request.user_session = user_session
                
                # Cleanup expired sessions periodically
                if self.should_cleanup():
                    self.cleanup_expired_sessions()
                    
        except Exception as e:
            logger.error(f"Session middleware error: {e}")
            # Don't break the request if session tracking fails
            pass
    
    def get_or_create_session(self, **kwargs):
        """Get or create session with proper concurrency handling"""
        try:
            # Try to find existing session
            session = UserSession.objects.get(
                user=kwargs['user'],
                session_key=kwargs['session_key'],
                browser_fingerprint=kwargs['browser_fingerprint'],
                session_context=kwargs['session_context']
            )
            return session
        except UserSession.DoesNotExist:
            # Create new session
            return UserSession.objects.create(**kwargs)
        except UserSession.MultipleObjectsReturned:
            # Handle edge case of duplicate sessions
            sessions = UserSession.objects.filter(
                user=kwargs['user'],
                session_key=kwargs['session_key'],
                browser_fingerprint=kwargs['browser_fingerprint'],
                session_context=kwargs['session_context']
            ).order_by('-last_activity')
            
            # Keep the most recent, deactivate others
            active_session = sessions.first()
            sessions.exclude(id=active_session.id).update(is_active=False, logout_reason='duplicate')
            return active_session
    
    def generate_browser_fingerprint(self, request):
        """Generate enhanced browser fingerprint for better uniqueness"""
        fingerprint_components = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
            request.META.get('HTTP_ACCEPT', ''),
            str(request.session.session_key or ''),
            # Add more entropy for concurrent sessions
            str(timezone.now().timestamp())[:10]  # 10-second precision
        ]
        
        fingerprint_string = '|'.join(fingerprint_components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:32]
    
    def generate_device_fingerprint(self, request):
        """Generate device-level fingerprint"""
        device_components = [
            request.META.get('HTTP_USER_AGENT', ''),
            self.get_client_ip(request),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
        ]
        
        device_string = '|'.join(device_components)
        return hashlib.md5(device_string.encode()).hexdigest()[:20]
    
    def get_or_create_tab_id(self, request):
        """Get or create unique tab identifier"""
        # In a real implementation, this would come from frontend JavaScript
        # For now, we'll use session key + timestamp for uniqueness
        if not hasattr(request.session, 'tab_id'):
            request.session['tab_id'] = str(uuid.uuid4())
        return request.session.get('tab_id', '')
    
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
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
    
    def should_cleanup(self):
        """Determine if cleanup should run (1% chance)"""
        import random
        return random.randint(1, 100) == 1
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            cutoff_time = timezone.now() - timezone.timedelta(hours=24)
            expired_count = UserSession.objects.filter(
                last_activity__lt=cutoff_time,
                is_active=True
            ).update(is_active=False, logout_reason='expired')
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")

class SessionTimeoutMiddleware(MiddlewareMixin):
    """
    Enterprise Session Timeout Middleware
    Enforces per-user session timeout settings
    """
    
    def process_request(self, request):
        """Check session timeout"""
        if not request.user.is_authenticated:
            return None
            
        if hasattr(request, 'user_session') and request.user_session:
            if request.user_session.is_expired:
                # Log timeout
                AccessLog.objects.create(
                    user=request.user,
                    action='logout',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details='Session timeout'
                )
                
                # Mark session as inactive
                request.user_session.is_active = False
                request.user_session.logout_reason = 'timeout'
                request.user_session.save()
                
                # Logout user
                from django.contrib.auth import logout
                logout(request)
                
                logger.info(f"Session timeout for user {request.user.username}")
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip