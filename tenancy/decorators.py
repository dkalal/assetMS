"""
Permission decorators for branch manager functionality.

Provides decorators to restrict access to manager-specific views and
enforce branch manager permissions.
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from tenancy.models import Branch


def branch_manager_required(view_func):
    """
    Decorator to ensure user is a branch manager.
    
    Checks if the authenticated user manages at least one active branch.
    If not, redirects to dashboard with an error message.
    
    Usage:
        @login_required
        @branch_manager_required
        def my_manager_view(request):
            # Only branch managers can access this
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('login')
        
        # Check if user manages any branches
        manages_branches = Branch.objects.filter(
            manager=request.user,
            is_active=True
        ).exists()
        
        if not manages_branches:
            messages.error(
                request,
                "You must be a branch manager to access this page."
            )
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def manages_branch(branch_id_param='branch_id'):
    """
    Decorator to ensure user manages the specific branch in the request.
    
    Args:
        branch_id_param: Name of the URL parameter containing branch ID
    
    Usage:
        @login_required
        @manages_branch('branch_id')
        def my_branch_view(request, branch_id):
            # Only the manager of this branch can access
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to access this page.")
                return redirect('login')
            
            # Get branch ID from kwargs
            branch_id = kwargs.get(branch_id_param)
            
            if not branch_id:
                messages.error(request, "Branch ID is required.")
                return redirect('dashboard')
            
            # Check if user manages this branch
            try:
                branch = Branch.objects.get(pk=branch_id, is_active=True)
                
                # Allow if user is the manager or an admin
                is_manager = branch.manager == request.user
                is_admin = getattr(request.user, 'role', None) == 'admin'
                is_superuser = request.user.is_superuser
                
                if not (is_manager or is_admin or is_superuser):
                    messages.error(
                        request,
                        f"You do not have permission to manage '{branch.name}'."
                    )
                    return redirect('dashboard')
                
            except Branch.DoesNotExist:
                messages.error(request, "Branch not found.")
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator


def manager_or_admin_required(view_func):
    """
    Decorator to ensure user has manager or admin role.
    
    This is less strict than branch_manager_required - it only checks
    the user's role, not whether they actually manage any branches.
    
    Usage:
        @login_required
        @manager_or_admin_required
        def my_view(request):
            # Only managers and admins can access
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('login')
        
        # Check role
        user_role = getattr(request.user, 'role', None)
        is_manager_or_admin = user_role in ['manager', 'admin']
        is_superuser = request.user.is_superuser
        
        if not (is_manager_or_admin or is_superuser):
            messages.error(
                request,
                "You must have manager or admin privileges to access this page."
            )
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
