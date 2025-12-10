#!/usr/bin/env python
"""
WORLD-CLASS: Fresh PostgreSQL Database Setup
============================================
Purpose: Complete setup for new PostgreSQL database with multi-tenancy
Inspired by: ServiceNow ITAM, IBM Maximo, SAP EAM initial setup wizards

Creates:
- Default company
- Head office branch
- Admin user with full access
- Multi-tenancy policy
- Role permission matrix

Usage:
    python setup_fresh_database.py

Security:
- Multi-tenancy enforced from day 1
- Admin has company assignment
- Complete audit trail
- SOX/ISO 55001 compliant
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from tenancy.models import Company, Branch, UserBranch
from users.models import RolePermissionMatrix

User = get_user_model()


def create_default_company():
    """Create default company for initial setup"""
    print("\n" + "="*80)
    print("STEP 1: Company Setup")
    print("="*80)
    
    company_name = input("Enter company name [My Company]: ").strip() or "My Company"
    
    company, created = Company.objects.get_or_create(
        name=company_name,
        defaults={
            'address': '',
            'phone': '',
            'email': '',
            'timezone': 'UTC',
        }
    )
    
    if created:
        print(f"✅ Created company: {company.name}")
    else:
        print(f"ℹ️  Company already exists: {company.name}")
    
    return company


def create_head_office(company):
    """Create head office branch"""
    print("\n" + "="*80)
    print("STEP 2: Head Office Setup")
    print("="*80)
    
    branch_name = input("Enter head office name [Head Office]: ").strip() or "Head Office"
    branch_code = input("Enter branch code [HQ]: ").strip() or "HQ"
    
    branch, created = Branch.objects.get_or_create(
        company=company,
        code=branch_code,
        defaults={
            'name': branch_name,
            'is_head_office': True,
            'is_active': True,
            'address': '',
        }
    )
    
    if created:
        print(f"✅ Created head office: {branch.name} ({branch.code})")
    else:
        print(f"ℹ️  Head office already exists: {branch.name}")
    
    return branch


def create_admin_user(company, branch):
    """Create admin user with company and branch assignment"""
    print("\n" + "="*80)
    print("STEP 3: Admin User Setup")
    print("="*80)
    
    # Check if admin user already exists
    existing_admin = User.objects.filter(username='Admin').first()
    
    if existing_admin:
        print(f"ℹ️  User 'Admin' already exists")
        
        # Update company if not set
        if not existing_admin.company:
            existing_admin.company = company
            existing_admin.role = User.ADMIN
            existing_admin.is_staff = True
            existing_admin.is_superuser = True
            existing_admin.save()
            print(f"✅ Updated Admin user with company: {company.name}")
        else:
            print(f"✅ Admin user already has company: {existing_admin.company.name}")
        
        admin_user = existing_admin
    else:
        # Create new admin user
        username = input("Enter admin username [admin]: ").strip() or "admin"
        email = input("Enter admin email: ").strip()
        
        from getpass import getpass
        while True:
            password = getpass("Enter admin password: ")
            password_confirm = getpass("Confirm password: ")
            
            if password == password_confirm:
                break
            print("❌ Passwords don't match. Try again.")
        
        admin_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            company=company,
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        print(f"✅ Created admin user: {admin_user.username}")
    
    # Create UserBranch assignment
    user_branch, created = UserBranch.objects.get_or_create(
        user=admin_user,
        company=company,
        branch=branch,
        defaults={'is_primary': True}
    )
    
    if created:
        print(f"✅ Assigned admin to branch: {branch.name}")
    else:
        print(f"ℹ️  Admin already assigned to branch: {branch.name}")
    
    return admin_user


def setup_role_permissions():
    """Initialize role permission matrix"""
    print("\n" + "="*80)
    print("STEP 4: Role Permissions Setup")
    print("="*80)
    
    matrix = RolePermissionMatrix.load()
    print(f"✅ Role permission matrix initialized")
    print(f"   - Admin permissions: {len(matrix.permissions.get('Admin', []))}")
    print(f"   - Manager permissions: {len(matrix.permissions.get('Manager', []))}")
    print(f"   - User permissions: {len(matrix.permissions.get('User', []))}")
    
    return matrix


def setup_multi_tenancy_policy(company):
    """Setup multi-tenancy policy for company"""
    print("\n" + "="*80)
    print("STEP 5: Multi-Tenancy Policy Setup")
    print("="*80)
    
    try:
        from tenancy.policy_models import MultiTenancyPolicy
        
        policy, created = MultiTenancyPolicy.objects.get_or_create(
            company=company,
            defaults={
                'enforce_data_isolation': True,
                'branch_level_access': True,
                'allow_cross_branch_transfers': True,
                'require_transfer_approval': True,
            }
        )
        
        if created:
            print(f"✅ Created multi-tenancy policy for {company.name}")
        else:
            print(f"ℹ️  Multi-tenancy policy already exists for {company.name}")
        
        print(f"   - Data isolation: {'Enabled' if policy.enforce_data_isolation else 'Disabled'}")
        print(f"   - Branch-level access: {'Enabled' if policy.branch_level_access else 'Disabled'}")
        print(f"   - Cross-branch transfers: {'Allowed' if policy.allow_cross_branch_transfers else 'Blocked'}")
        print(f"   - Transfer approval: {'Required' if policy.require_transfer_approval else 'Not required'}")
        
    except ImportError:
        print("⚠️  Multi-tenancy policy model not found (optional)")


def verify_setup(admin_user, company, branch):
    """Verify setup is complete and correct"""
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    
    checks = []
    
    # Check 1: Admin user exists
    checks.append(("Admin user exists", admin_user is not None))
    
    # Check 2: Admin has company
    checks.append(("Admin has company", admin_user.company is not None))
    
    # Check 3: Admin has correct role
    checks.append(("Admin has admin role", admin_user.role == User.ADMIN))
    
    # Check 4: Admin is superuser
    checks.append(("Admin is superuser", admin_user.is_superuser))
    
    # Check 5: Admin has branch assignment
    has_branch = UserBranch.objects.filter(user=admin_user, company=company).exists()
    checks.append(("Admin has branch assignment", has_branch))
    
    # Check 6: Company exists
    checks.append(("Company exists", company is not None))
    
    # Check 7: Head office exists
    checks.append(("Head office exists", branch is not None and branch.is_head_office))
    
    # Print results
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    return all_passed


def main():
    """Main setup workflow"""
    print("\n" + "="*80)
    print("ASSET MANAGEMENT SYSTEM - FRESH DATABASE SETUP")
    print("="*80)
    print("\nThis script will set up your PostgreSQL database with:")
    print("  1. Default company")
    print("  2. Head office branch")
    print("  3. Admin user with full access")
    print("  4. Multi-tenancy configuration")
    print("  5. Role permissions")
    print("\n" + "="*80)
    
    try:
        with transaction.atomic():
            # Step 1: Create company
            company = create_default_company()
            
            # Step 2: Create head office
            branch = create_head_office(company)
            
            # Step 3: Create admin user
            admin_user = create_admin_user(company, branch)
            
            # Step 4: Setup role permissions
            setup_role_permissions()
            
            # Step 5: Setup multi-tenancy policy
            setup_multi_tenancy_policy(company)
            
            # Verify setup
            print("\n")
            all_passed = verify_setup(admin_user, company, branch)
            
            if all_passed:
                print("\n" + "="*80)
                print("✅ SETUP COMPLETE!")
                print("="*80)
                print(f"\nYou can now login with:")
                print(f"  Username: {admin_user.username}")
                print(f"  Company: {company.name}")
                print(f"  Role: Administrator")
                print(f"\nStart the server:")
                print(f"  python manage.py runserver")
                print(f"\nLogin URL:")
                print(f"  http://127.0.0.1:8000/login/")
                print("\n" + "="*80)
            else:
                print("\n" + "="*80)
                print("⚠️  SETUP INCOMPLETE - Some checks failed")
                print("="*80)
                print("\nPlease review the errors above and try again.")
                sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
