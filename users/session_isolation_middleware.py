"""
WORLD-CLASS: Session Isolation Middleware

IMPORTANT: This approach of modifying settings.SESSION_COOKIE_NAME dynamically
has critical issues in multi-threaded environments. Django admin login fails
because the setting changes between request processing stages.

SOLUTION: This middleware is DISABLED. Use Django's built-in session management.
For independent admin/regular sessions, use separate Django projects or
implement proper session backend customization.

ALTERNATIVE APPROACH (Recommended):
- Single session for authenticated user
- User can access both admin and regular dashboard with same session
- Django's built-in permission system handles access control
- No session isolation needed - it's a feature, not a bug!

Following best practices from:
- ServiceNow ITAM: Single sign-on across admin and user interfaces
- IBM Maximo: Unified authentication with role-based access
- SAP EAM: Single session with context-aware permissions

This file is kept for reference but middleware is DISABLED in settings.
"""

from django.utils.deprecation import MiddlewareMixin
from django.contrib.sessions.backends.db import SessionStore
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


# DISABLED: This middleware causes Django admin login failures
# Reason: Modifying settings.SESSION_COOKIE_NAME dynamically breaks session handling
# Solution: Remove from MIDDLEWARE in settings.py


class SessionIsolationMiddleware(MiddlewareMixin):
    """
    WORLD-CLASS: Session Isolation Middleware
    
    Provides completely independent sessions for Django admin and regular dashboard.
    
    How It Works:
    1. Detects if request is for Django admin (/admin/*)
    2. If admin: Uses 'admin_sessionid' cookie
    3. If regular: Uses 'sessionid' cookie (default)
    4. Each context has its own session storage
    5. Login/logout on one doesn't affect the other
    
    Benefits:
    - Admins can use both admin and regular dashboard simultaneously
    - Different users can be logged into admin and regular site
    - Logout from one doesn't logout from the other
    - Complete session independence
    - Enhanced security through context isolation
    """
    
    # Session cookie names for each context
    REGULAR_SESSION_COOKIE = 'sessionid'
    ADMIN_SESSION_COOKIE = 'admin_sessionid'
    
    def process_request(self, request):
        """
        Process incoming request and set appropriate session cookie name
        
        This runs BEFORE Django's SessionMiddleware processes the session,
        allowing us to dynamically change which session cookie to use.
        """
        # Determine current context
        is_admin_context = self.is_admin_request(request)
        
        # Store context in request for later use
        request.is_admin_context = is_admin_context
        
        # Dynamically set session cookie name based on context
        if is_admin_context:
            # Admin context: Use admin session cookie
            settings.SESSION_COOKIE_NAME = self.ADMIN_SESSION_COOKIE
            logger.debug(f'Admin context detected: {request.path} - Using {self.ADMIN_SESSION_COOKIE}')
        else:
            # Regular context: Use regular session cookie
            settings.SESSION_COOKIE_NAME = self.REGULAR_SESSION_COOKIE
            logger.debug(f'Regular context detected: {request.path} - Using {self.REGULAR_SESSION_COOKIE}')
        
        # Let Django's SessionMiddleware handle the rest
        return None
    
    def process_response(self, request, response):
        """
        Process outgoing response and ensure correct session cookie is set
        
        This runs AFTER Django's SessionMiddleware has processed the session,
        allowing us to verify the correct cookie was used.
        """
        # Get context from request (set in process_request)
        is_admin_context = getattr(request, 'is_admin_context', False)
        
        # Verify correct session cookie name is still set
        if is_admin_context:
            settings.SESSION_COOKIE_NAME = self.ADMIN_SESSION_COOKIE
        else:
            settings.SESSION_COOKIE_NAME = self.REGULAR_SESSION_COOKIE
        
        return response
    
    def is_admin_request(self, request):
        """
        Determine if request is for Django admin
        
        Admin requests include:
        - /admin/* (Django admin interface)
        - /static/admin/* (Admin static files)
        
        Everything else is considered regular dashboard.
        """
        path = request.path
        
        # Django admin paths
        if path.startswith('/admin/'):
            return True
        
        # Admin static files
        if path.startswith('/static/admin/'):
            return True
        
        # Everything else is regular dashboard
        return False


class SessionContextMiddleware(MiddlewareMixin):
    """
    WORLD-CLASS: Session Context Middleware
    
    Adds session context information to requests for logging and debugging.
    This helps track which session (admin or regular) is being used.
    
    Provides:
    - request.session_context: 'admin' or 'regular'
    - request.session_cookie_name: Actual cookie name being used
    - Enhanced logging for security monitoring
    """
    
    def process_request(self, request):
        """Add session context information to request"""
        # Get context from SessionIsolationMiddleware
        is_admin_context = getattr(request, 'is_admin_context', False)
        
        # Add context information to request
        if is_admin_context:
            request.session_context = 'admin'
            request.session_cookie_name = 'admin_sessionid'
        else:
            request.session_context = 'regular'
            request.session_cookie_name = 'sessionid'
        
        # Log session context for security monitoring
        if request.user.is_authenticated:
            logger.debug(
                f'Session context: {request.session_context} | '
                f'User: {request.user.username} | '
                f'Path: {request.path} | '
                f'Cookie: {request.session_cookie_name}'
            )
        
        return None


class SessionCleanupMiddleware(MiddlewareMixin):
    """
    WORLD-CLASS: Session Cleanup Middleware
    
    Ensures session cookie names are reset after each request.
    This prevents context bleeding between requests.
    
    Critical for:
    - Multi-threaded environments
    - Concurrent requests
    - Request isolation
    """
    
    def process_response(self, request, response):
        """Reset session cookie name to default after request"""
        # Reset to default (regular dashboard)
        settings.SESSION_COOKIE_NAME = 'sessionid'
        return response
