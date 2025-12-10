"""
Context Processors for Accounts
================================
Purpose: Make trial status and company info available in all templates
Pattern: Django best practice for global template variables
"""

from accounts.models import CompanyRegistration


def trial_status(request):
    """
    Add trial status information to template context
    
    Usage in templates:
        {% if trial_info.is_trial %}
            <div class="alert alert-warning">
                {{ trial_info.message }}
            </div>
        {% endif %}
    """
    
    # Default context
    context = {
        'trial_info': {
            'is_trial': False,
            'is_expired': False,
            'is_warning': False,
            'days_left': None,
            'message': None,
            'status': 'unknown',
        }
    }
    
    # Only for authenticated users with company
    if not request.user.is_authenticated or not request.user.company:
        return context
    
    # Skip for system admins
    if request.user.is_system_admin and not request.user.company:
        return context
    
    try:
        registration = CompanyRegistration.objects.get(company=request.user.company)
        
        if registration.subscription_status == 'trial':
            days_left = registration.days_until_trial_ends()
            
            context['trial_info'] = {
                'is_trial': True,
                'is_expired': days_left is not None and days_left <= 0,
                'is_warning': days_left is not None and 0 < days_left <= 7,
                'days_left': days_left,
                'message': registration.get_trial_status_message(),
                'status': 'trial',
                'plan': registration.get_plan_display(),
            }
        elif registration.subscription_status == 'suspended':
            context['trial_info'] = {
                'is_trial': False,
                'is_expired': True,
                'is_warning': False,
                'days_left': 0,
                'message': 'Your account has been suspended. Please contact support.',
                'status': 'suspended',
                'plan': registration.get_plan_display(),
            }
        else:
            context['trial_info'] = {
                'is_trial': False,
                'is_expired': False,
                'is_warning': False,
                'days_left': None,
                'message': None,
                'status': registration.subscription_status,
                'plan': registration.get_plan_display(),
            }
    
    except CompanyRegistration.DoesNotExist:
        # No registration found - allow access
        pass
    
    return context


def company_limits(request):
    """
    Add resource limit information to template context
    
    Usage in templates:
        {% if limits.users_near_limit %}
            <div class="alert alert-info">
                You're using {{ limits.users_current }}/{{ limits.users_max }} users
            </div>
        {% endif %}
    """
    
    context = {
        'limits': {
            'users_current': 0,
            'users_max': 0,
            'users_near_limit': False,
            'assets_current': 0,
            'assets_max': 0,
            'assets_near_limit': False,
        }
    }
    
    # Only for authenticated users with company
    if not request.user.is_authenticated or not request.user.company:
        return context
    
    try:
        registration = CompanyRegistration.objects.get(company=request.user.company)
        
        # Get current counts
        from users.models import User
        from assets.models import Asset
        
        users_current = User.objects.filter(company=request.user.company).count()
        assets_current = Asset.objects.filter(company=request.user.company).count()
        
        # Calculate limits
        users_max = registration.max_users if registration.max_users != -1 else float('inf')
        assets_max = registration.max_assets if registration.max_assets != -1 else float('inf')
        
        # Check if near limit (80% threshold)
        users_near_limit = users_max != float('inf') and users_current >= (users_max * 0.8)
        assets_near_limit = assets_max != float('inf') and assets_current >= (assets_max * 0.8)
        
        context['limits'] = {
            'users_current': users_current,
            'users_max': users_max if users_max != float('inf') else 'Unlimited',
            'users_near_limit': users_near_limit,
            'users_percentage': int((users_current / users_max * 100)) if users_max != float('inf') else 0,
            'assets_current': assets_current,
            'assets_max': assets_max if assets_max != float('inf') else 'Unlimited',
            'assets_near_limit': assets_near_limit,
            'assets_percentage': int((assets_current / assets_max * 100)) if assets_max != float('inf') else 0,
        }
    
    except CompanyRegistration.DoesNotExist:
        pass
    
    return context
