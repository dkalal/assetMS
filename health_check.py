"""
Simple health check view for Docker health checks.
Add this to your main urls.py:

from health_check import health_check
urlpatterns = [
    # ... your existing patterns
    path('health/', health_check, name='health_check'),
]
"""

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Simple health check endpoint that verifies:
    - Database connectivity
    - Basic application responsiveness
    Returns 200 OK if healthy, 503 Service Unavailable if not
    """
    try:
        # Check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Basic response
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        }, status=200)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)