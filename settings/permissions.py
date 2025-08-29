"""
Enterprise Role-Based Settings Permissions
Implements granular access control for different user roles
"""
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

class SettingsPermissions:
    """Enterprise settings permission matrix"""
    
    ADMIN_SETTINGS = [
        'system_settings',
        'organization_settings', 
        'user_management',
        'session_management',
        'security_settings',
        'privacy_settings',
        'backup_restore',
        'email_configuration',
        'audit_logs'
    ]
    
    MANAGER_SETTINGS = [
        'organization_settings',
        'custom_fields',
        'department_settings',
        'reporting_settings'
    ]
    
    USER_SETTINGS = [
        'personal_profile',
        'account_security',
        'notification_preferences',
        'privacy_preferences'
    ]
    
    @classmethod
    def can_access_setting(cls, user, setting_type):
        """Check if user can access specific setting type"""
        if not user.is_authenticated:
            return False
            
        if user.role == 'admin':
            return setting_type in cls.ADMIN_SETTINGS
        elif user.role == 'manager':
            return setting_type in cls.MANAGER_SETTINGS
        else:
            return setting_type in cls.USER_SETTINGS
    
    @classmethod
    def get_available_settings(cls, user):
        """Get list of settings available to user"""
        if not user.is_authenticated:
            return []
            
        if user.role == 'admin':
            return cls.ADMIN_SETTINGS
        elif user.role == 'manager':
            return cls.MANAGER_SETTINGS
        else:
            return cls.USER_SETTINGS

def require_setting_permission(setting_type):
    """Decorator to enforce setting-specific permissions"""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not SettingsPermissions.can_access_setting(request.user, setting_type):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'error': 'Access denied',
                        'error_code': 'INSUFFICIENT_PERMISSIONS'
                    }, status=403)
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator