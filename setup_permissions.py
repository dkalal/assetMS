#!/usr/bin/env python
"""
Enterprise Permission Setup Script
Run this after initial migration to setup permissions system
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from django.core.management import call_command
from users.models import User
from users.permissions import UserPermissionManager

def main():
    print("🚀 Setting up Enterprise Permission System...")
    
    # Run the setup permissions command
    try:
        call_command('setup_permissions')
        print("✅ Permissions and groups created successfully")
    except Exception as e:
        print(f"❌ Error setting up permissions: {e}")
        return
    
    # Update existing users
    try:
        users_updated = 0
        for user in User.objects.all():
            UserPermissionManager.update_user_permissions(user, user.role)
            users_updated += 1
        
        print(f"✅ Updated permissions for {users_updated} users")
    except Exception as e:
        print(f"❌ Error updating user permissions: {e}")
        return
    
    print("🎉 Permission system setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Test the permissions modal in the profile page")
    print("2. Verify role-based access control")
    print("3. Check audit logging for permission changes")

if __name__ == '__main__':
    main()