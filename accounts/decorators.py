"""
Account Management Decorators
===============================
Purpose: Security decorators for views (rate limiting, email verification, system admin)
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.cache import cache
from .utils import get_client_ip, check_rate_limit


def rate_limit_registration(limit=5, window_seconds=3600):
    """
    Rate limit decorator for registration endpoint.
    
    Limits: 5 signups per hour per IP (default).
    
    Args:
        limit: Maximum number of attempts
        window_seconds: Time window in seconds (default: 3600 = 1 hour)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method == 'POST':
                ip = get_client_ip(request)
                key = f'registration:{ip}'
                
                is_allowed, remaining, reset_time = check_rate_limit(key, limit, window_seconds)
                
                if not is_allowed:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'error': 'Too many registration attempts. Please try again later.',
                            'reset_time': reset_time.isoformat()
                        }, status=429)
                    
                    messages.error(
                        request,
                        f'Too many registration attempts. Please try again after {reset_time.strftime("%H:%M")}.'
                    )
                    return redirect('accounts:register')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def email_verification_required(view_func):
    """
    Decorator to enforce email verification before accessing view.
    
    Redirects unverified users to verification page.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if not request.user.email_verified:
                messages.warning(
                    request,
                    'Please verify your email address to continue.'
                )
                return redirect('accounts:verify_email_sent')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def system_admin_required(view_func):
    """
    Decorator to enforce system admin access.
    
    Only allows users with is_system_admin=True and company=None.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        if not (request.user.is_system_admin and request.user.company is None):
            messages.error(request, 'Access denied. System admin privileges required.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def company_required(view_func):
    """
    Decorator to enforce company assignment.
    
    Redirects users without company to setup wizard.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_system_admin:
                # System admin bypasses company requirement
                return view_func(request, *args, **kwargs)
            
            if not request.user.company:
                messages.warning(request, 'Please complete company setup to continue.')
                return redirect('tenant_setup_wizard')
        
        return view_func(request, *args, **kwargs)
    return wrapper








