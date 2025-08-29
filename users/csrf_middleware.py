from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
import logging

logger = logging.getLogger(__name__)

class EnterpriseCSRFMiddleware(MiddlewareMixin):
    """
    Enterprise CSRF Middleware
    Ensures CSRF tokens are properly handled for login pages
    """
    
    def process_request(self, request):
        """Ensure CSRF token is available for login pages"""
        if self.is_login_page(request):
            # Force CSRF token generation
            get_token(request)
            
            # Log CSRF token generation for security monitoring
            logger.info(f"CSRF token generated for login attempt from {self.get_client_ip(request)}")
    
    def process_response(self, request, response):
        """Add security headers for login pages"""
        if self.is_login_page(request):
            response['X-Frame-Options'] = 'DENY'
            response['X-Content-Type-Options'] = 'nosniff'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    
    def is_login_page(self, request):
        """Check if current request is for login page"""
        login_paths = ['/login/', '/accounts/login/']
        return (
            request.path in login_paths or 
            (hasattr(request, 'resolver_match') and 
             request.resolver_match and 
             request.resolver_match.url_name == 'login')
        )
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip