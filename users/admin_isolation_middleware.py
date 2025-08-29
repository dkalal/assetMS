from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

class AdminSessionIsolationMiddleware(MiddlewareMixin):
    """
    Enterprise Admin Session Isolation Middleware
    Prevents admin users from accessing regular site with admin session
    """
    
    def process_request(self, request):
        """Enforce admin session isolation"""
        if not request.user.is_authenticated:
            return None
            
        # Get current session context
        current_context = self.get_current_context(request)
        
        # Check if user has admin session but accessing non-admin area
        if hasattr(request, 'user_session'):
            session_context = getattr(request.user_session, 'session_context', 'web')
            
            # Admin session trying to access web app
            if session_context == 'admin' and current_context == 'web':
                return self.handle_context_violation(request, 'admin_to_web')
            
            # Web session trying to access admin (Django handles this, but we log it)
            elif session_context == 'web' and current_context == 'admin':
                if not (request.user.is_superuser or request.user.role == 'admin'):
                    logger.warning(f'Web session user {request.user.username} attempted admin access')
                    return self.handle_context_violation(request, 'web_to_admin')
        
        return None
    
    def get_current_context(self, request):
        """Determine current request context"""
        path = request.path
        
        if path.startswith('/admin/'):
            return 'admin'
        elif path.startswith('/api/'):
            return 'api'
        else:
            return 'web'
    
    def handle_context_violation(self, request, violation_type):
        """Handle context access violations"""
        user = request.user
        ip_address = self.get_client_ip(request)
        
        # Log security violation
        logger.warning(f'Context violation: {violation_type} by {user.username} from {ip_address}')
        
        # Create access log entry
        from users.models import AccessLog
        AccessLog.objects.create(
            user=user,
            action='failed_login',
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details=f'Context violation: {violation_type}'
        )
        
        # Logout user and redirect with message
        logout(request)
        
        if violation_type == 'admin_to_web':
            messages.error(request, 
                'Security Notice: Admin sessions cannot access the main application. '
                'Please login with a regular account to access the dashboard.'
            )
            return redirect('users:login')
        
        elif violation_type == 'web_to_admin':
            messages.error(request, 
                'Access Denied: You do not have permission to access the admin panel.'
            )
            return redirect('users:login')
        
        return None
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip