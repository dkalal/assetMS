from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.db import models
from .models import User

class UserPermissionManager:
    """Enterprise-level permission management system"""
    
    PERMISSION_MATRIX = {
        'admin': [
            'view_asset', 'add_asset', 'change_asset', 'delete_asset',
            'view_user', 'add_user', 'change_user', 'delete_user',
            'view_auditlog', 'add_auditlog', 'change_auditlog',
            'view_assetcategory', 'add_assetcategory', 'change_assetcategory', 'delete_assetcategory',
            'view_reports', 'export_data', 'backup_system', 'restore_system'
        ],
        'manager': [
            'view_asset', 'add_asset', 'change_asset',
            'view_user', 'change_user',
            'view_auditlog',
            'view_assetcategory', 'add_assetcategory',
            'view_reports', 'export_data'
        ],
        'user': [
            'view_asset', 'view_auditlog'
        ]
    }
    
    @classmethod
    def get_role_permissions(cls, role):
        """Get permissions for a specific role"""
        return cls.PERMISSION_MATRIX.get(role, [])
    
    @classmethod
    def update_user_permissions(cls, user, new_role):
        """Update user permissions based on role"""
        # Clear existing permissions
        user.user_permissions.clear()
        user.groups.clear()
        
        # Get or create role group
        group, created = Group.objects.get_or_create(name=new_role.title())
        
        # Add permissions to group if newly created
        if created:
            permissions = cls.get_role_permissions(new_role)
            for perm_codename in permissions:
                try:
                    permission = Permission.objects.get(codename=perm_codename)
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    continue
        
        # Add user to group
        user.groups.add(group)
        user.role = new_role
        user.save()
        
        return True
    
    @classmethod
    def get_user_permissions_summary(cls, user):
        """Get comprehensive permission summary for user"""
        return {
            'role': user.role,
            'permissions': list(user.get_all_permissions()),
            'groups': [g.name for g in user.groups.all()],
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff
        }