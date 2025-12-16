from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


def _is_admin(user):
    """Return True when the user has admin-level privileges."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True
    if getattr(user, 'is_system_admin', False):
        return True
    try:
        from .models import User
    except Exception:  # pragma: no cover - defensive import guard
        return False
    return getattr(user, 'role', None) == User.ADMIN


def _is_manager_or_admin(user):
    """Return True when the user is a manager or admin within their company."""
    if _is_admin(user):
        return True
    try:
        from .models import User
    except Exception:  # pragma: no cover
        return False
    return getattr(user, 'role', None) in {User.MANAGER, User.ADMIN}


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
    """Decorator for API views that require admin privileges (role-aware)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTHENTICATION_REQUIRED'
            }, status=401)

        if not _is_admin(request.user):
            return JsonResponse({
                'success': False,
                'error': 'Admin privileges required',
                'code': 'INSUFFICIENT_PERMISSIONS'
            }, status=403)

        return view_func(request, *args, **kwargs)
    return wrapper


def api_admin_or_manager_required(view_func):
    """Decorator for API views that require admin or manager privileges."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTHENTICATION_REQUIRED'
            }, status=401)

        if not _is_manager_or_admin(request.user):
            return JsonResponse({
                'success': False,
                'error': 'Manager or admin privileges required',
                'code': 'INSUFFICIENT_PERMISSIONS'
            }, status=403)

        return view_func(request, *args, **kwargs)
    return wrapper


def api_manager_or_admin_required(view_func):
    """
    Decorator for API views that require manager or admin role
    Checks User.role field (MANAGER or ADMIN)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTHENTICATION_REQUIRED'
            }, status=401)

        if not _is_manager_or_admin(request.user):
            return JsonResponse({
                'success': False,
                'error': 'Manager or Admin role required',
                'code': 'INSUFFICIENT_PERMISSIONS'
            }, status=403)

        return view_func(request, *args, **kwargs)
    return wrapper