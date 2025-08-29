from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

class LoginPageSecurityMiddleware(MiddlewareMixin):
    """
    Enterprise Login Page Security Middleware
    Prevents authenticated users from accessing login page
    Clears any existing sessions when accessing login
    """
    
    def process_request(self, request):
        """Secure login page access"""
        # Check if this is the login page
        if self.is_login_page(request):
            return self.handle_login_page_access(request)
        
        return None
    
    def is_login_page(self, request):
        """Check if current request is for login page"""
        login_paths = ['/login/', '/accounts/login/']
        return request.path in login_paths or (
            hasattr(request, 'resolver_match') and 
            request.resolver_match and 
            request.resolver_match.url_name == 'login'
        )
    
    def handle_login_page_access(self, request):
        """Handle access to login page with security measures"""
        # If user is already authenticated, handle appropriately
        if request.user.is_authenticated:
            # Log the attempt
            logger.info(f"Authenticated user {request.user.username} accessed login page")
            
            # Option 1: Redirect to dashboard (recommended for UX)
            return redirect('dashboard')
            
            # Option 2: Force logout and show login (uncomment if preferred)
            # logout(request)
            # logger.info(f"Forced logout of user {request.user.username} on login page access")
        
        # Clear any session data that might leak information
        self.clear_sensitive_session_data(request)
        
        return None
    
    def clear_sensitive_session_data(self, request):
        """Clear sensitive session data on login page"""
        sensitive_keys = [
            'last_user_info',
            'previous_user',
            'user_preferences',
            'cached_user_data'
        ]
        
        for key in sensitive_keys:
            if key in request.session:
                del request.session[key]
    
    def process_response(self, request, response):
        """Process response for login page"""
        if self.is_login_page(request):
            # Add security headers for login page
            response['X-Frame-Options'] = 'DENY'
            response['X-Content-Type-Options'] = 'nosniff'
            response['Referrer-Policy'] = 'no-referrer'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response