import time
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Enterprise-level performance monitoring for API endpoints"""
    
    def process_request(self, request):
        request.start_time = time.time()
        
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log slow API requests
            if request.path.startswith('/api/') and duration > 1.0:
                logger.warning(f"Slow API request: {request.path} took {duration:.2f}s")
            
            # Add performance headers for monitoring
            response['X-Response-Time'] = f"{duration:.3f}s"
            
        return response

class APIErrorHandlingMiddleware(MiddlewareMixin):
    """Enterprise-level error handling for API endpoints"""
    
    def process_exception(self, request, exception):
        if request.path.startswith('/api/'):
            logger.error(f"API Error in {request.path}: {str(exception)}", exc_info=True)
            
            return JsonResponse({
                'success': False,
                'error': 'An internal error occurred. Please try again later.',
                'error_code': 'INTERNAL_ERROR'
            }, status=500)
        
        return None