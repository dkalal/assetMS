"""
Permission decorators for multi-tenancy and branch manager functionality.

Provides decorators to enforce multi-tenancy, restrict access to manager-specific
views, and enforce branch manager permissions.

World-Class Multi-Tenancy Standards (ServiceNow, Salesforce, IBM Maximo)
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseForbidden

from tenancy.models import Branch, Company


def company_required(view_func):
    """
    Decorator to enforce multi-tenancy by ensuring user has a company.
    
    Automatically attaches the user's company to the request object as request.company.
    This is a foundational decorator for all multi-tenant views.
    
    World-Class Multi-Tenancy Pattern (ServiceNow, Salesforce, IBM Maximo):
    - Every request must be scoped to a company
    - Company is attached to request for easy access
    - Prevents cross-tenant data leakage
    - Provides clear error messages
    
    Usage:
        @login_required
        @company_required
        def my_view(request):
            company = request.company  # Automatically available
            assets = Asset.objects.filter(company=company)
            return render(request, 'template.html', {'assets': assets})
    
    Security:
        - Enforces multi-tenancy at decorator level
        - Prevents accidental cross-tenant queries
        - Fails fast if company is missing
        - Provides user-friendly error messages
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check authentication
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('login')
        
        # Get user's company
        company = getattr(request.user, 'company', None)
        
        if not company:
            # User has no company - critical error
            messages.error(
                request,
                "Your account is not associated with a company. "
                "Please contact your administrator."
            )
            return redirect('dashboard')
        
        # Attach company to request for easy access in view
        request.company = company
        
        # Call the view
        return view_func(request, *args, **kwargs)
    
    return wrapper


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
