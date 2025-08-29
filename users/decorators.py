from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

def api_login_required(view_func):
    """
    Decorator for API views that require authentication
    Returns JSON response for unauthenticated requests
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTHENTICATION_REQUIRED'
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

def api_admin_required(view_func):
    """
    Decorator for API views that require admin privileges
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTHENTICATION_REQUIRED'
            }, status=401)
        
        if not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Admin privileges required',
                'code': 'INSUFFICIENT_PERMISSIONS'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapper

def api_admin_or_manager_required(view_func):
    """
    Decorator for API views that require admin or manager privileges
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTHENTICATION_REQUIRED'
            }, status=401)
        
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({
                'success': False,
                'error': 'Manager or admin privileges required',
                'code': 'INSUFFICIENT_PERMISSIONS'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapper