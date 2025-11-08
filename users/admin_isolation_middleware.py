from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

class AdminSessionIsolationMiddleware(MiddlewareMixin):
    """
    WORLD-CLASS: Enterprise Admin Session Isolation Middleware
    
    NOTE: With independent sessions (SessionIsolationMiddleware), this middleware
    is now primarily for logging and monitoring. Session isolation is handled
    automatically by separate session cookies.
    
    This middleware now provides:
    - Security monitoring and logging
    - Access attempt tracking
    - Audit trail for admin access
    
    Following best practices from:
    - ServiceNow ITAM: Separate admin and user contexts
    - IBM Maximo: Admin console isolation
    - SAP EAM: Role-based session management
    
    Note: Sessions are now completely independent via SessionIsolationMiddleware.
    Users can be logged into both admin and regular dashboard simultaneously.
    """
    
    def process_request(self, request):
        """Monitor and log admin access attempts"""
        if not request.user.is_authenticated:
            return None
        
        # Get current session context (set by SessionContextMiddleware)
        session_context = getattr(request, 'session_context', 'regular')
        current_path = request.path
        
        # Log admin access for security monitoring
        if current_path.startswith('/admin/') and session_context == 'admin':
            logger.info(
                f'Admin access: {request.user.username} | '
                f'Path: {current_path} | '
                f'IP: {self.get_client_ip(request)}'
            )
        
        # Log if non-admin user tries to access admin (Django will handle rejection)
        if current_path.startswith('/admin/'):
            if not (request.user.is_superuser or getattr(request.user, 'is_staff', False)):
                logger.warning(
                    f'Unauthorized admin access attempt: {request.user.username} | '
                    f'Path: {current_path} | '
                    f'IP: {self.get_client_ip(request)}'
                )
        
        return None
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
    
    # REMOVED: process_response method
    # Django's built-in CSRF middleware already handles token rotation correctly
    # Manual rotation was causing tokens to be invalidated before form submission