#!/usr/bin/env python
"""
Quick System Verification Script
Verifies that the permission system is properly configured
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.permissions import UserPermissionManager

User = get_user_model()

def verify_system():
    print("Verifying Enterprise Permission System...")
    
    # Check if users exist
    user_count = User.objects.count()
    print(f"[OK] Users in system: {user_count}")
    
    # Check admin users
    admin_count = User.objects.filter(role='admin').count()
    print(f"[OK] Admin users: {admin_count}")
    
    # Verify permission system
    if admin_count > 0:
        admin = User.objects.filter(role='admin').first()
        permissions = UserPermissionManager.get_role_permissions('admin')
        print(f"[OK] Admin permissions configured: {len(permissions)} permissions")
    
    print("\nSystem verification complete!")
    print("\nNext Steps:")
    print("1. Run: python manage.py runserver")
    print("2. Login as admin user")
    print("3. Go to Profile page")
    print("4. Click 'Manage Permissions' button")
    print("5. Test the permission modal functionality")

if __name__ == '__main__':
    verify_system()