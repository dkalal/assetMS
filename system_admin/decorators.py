"""
System Admin Decorators
=======================
Purpose: Decorators for system admin access control
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


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








