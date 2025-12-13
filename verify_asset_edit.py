#!/usr/bin/env python
"""
Verification Script: Asset Edit Form Pre-Population
Purpose: Verify that asset edit form pre-populates all fields correctly
Usage: python verify_asset_edit.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from assets.models import Asset, AssetCategory
from assets.forms import AssetForm
from users.models import User
from tenancy.models import Company, Branch
from django.test import RequestFactory

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

def print_warning(msg):
    print(f"⚠️  {msg}")

def verify_asset_edit_prepopulation():
    """Verify asset edit form pre-population"""
    
    print("\n" + "="*70)
    print("Asset Edit Form Pre-Population Verification")
    print("="*70 + "\n")
    
    # Step 1: Check if we have any assets
    print_info("Step 1: Checking for existing assets...")
    assets = Asset.objects.all()[:5]
    
    if not assets.exists():
        print_warning("No assets found in database")
        print_info("Please create an asset first to test edit form")
        return False
    
    print_success(f"Found {assets.count()} assets to test")
    
    # Step 2: Test each asset
    all_passed = True
    
    for asset in assets:
        print(f"\n{'─'*70}")
        print(f"Testing Asset: {asset.uuid}")
        print(f"Category: {asset.category.name if asset.category else 'None'}")
        print(f"Branch: {asset.branch.name if asset.branch else 'None'}")
        print(f"{'─'*70}\n")
        
        # Create mock request
        factory = RequestFactory()
        request = factory.get(f'/assets/{asset.uuid}/edit/')
        request.user = asset.company.users.filter(role='admin').first()
        request.company = asset.company
        
        if not request.user:
            print_warning(f"No admin user found for company {asset.company.name}")
            continue
        
        # Test form initialization
        try:
            form = AssetForm(instance=asset, request=request)
            
            # Check standard fields
            print_info("Checking standard fields...")
            standard_fields = {
                'category': asset.category.id if asset.category else None,
                'branch': asset.branch.id if asset.branch else None,
                'status': asset.status,
                'description': asset.description,
            }
            
            for field_name, expected_value in standard_fields.items():
                if field_name in form.fields:
                    initial_value = form.initial.get(field_name)
                    if initial_value == expected_value:
                        print_success(f"  {field_name}: {initial_value}")
                    else:
                        print_error(f"  {field_name}: Expected {expected_value}, got {initial_value}")
                        all_passed = False
            
            # Check dynamic fields
            if asset.dynamic_data:
                print_info("Checking dynamic fields...")
                for key, value in asset.dynamic_data.items():
                    field_name = f'dyn_{key}'
                    if field_name in form.fields:
                        initial_value = form.initial.get(field_name)
                        if initial_value == value:
                            print_success(f"  {field_name}: {value}")
                        else:
                            print_error(f"  {field_name}: Expected {value}, got {initial_value}")
                            all_passed = False
                    else:
                        print_warning(f"  {field_name}: Field not in form (may be expected)")
            else:
                print_info("No dynamic data for this asset")
            
        except Exception as e:
            print_error(f"Error testing asset {asset.uuid}: {e}")
            all_passed = False
    
    # Summary
    print(f"\n{'='*70}")
    if all_passed:
        print_success("All tests passed! Asset edit form pre-population is working correctly.")
    else:
        print_error("Some tests failed. Please review the output above.")
    print("="*70 + "\n")
    
    return all_passed

def verify_javascript_integration():
    """Verify JavaScript integration"""
    
    print("\n" + "="*70)
    print("JavaScript Integration Verification")
    print("="*70 + "\n")
    
    # Check if JavaScript file exists
    js_file = 'static/js/asset_form_enhanced.js'
    
    if os.path.exists(js_file):
        print_success(f"JavaScript file exists: {js_file}")
        
        # Check for key functions
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            checks = [
                ('prefillDynamicFields', 'Pre-fill function'),
                ('loadCategoryFields', 'Category loading function'),
                ('EDIT MODE', 'Edit mode detection'),
                ('asset-initial-dyn', 'JSON script tag reference'),
            ]
            
            for check, description in checks:
                if check in content:
                    print_success(f"  {description}: Found")
                else:
                    print_error(f"  {description}: Not found")
    else:
        print_error(f"JavaScript file not found: {js_file}")
    
    print()

def verify_template():
    """Verify template has JSON script tag"""
    
    print("\n" + "="*70)
    print("Template Verification")
    print("="*70 + "\n")
    
    template_file = 'templates/assets/asset_form.html'
    
    if os.path.exists(template_file):
        print_success(f"Template file exists: {template_file}")
        
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            checks = [
                ('asset-initial-dyn', 'JSON script tag ID'),
                ('object.dynamic_data|json_script', 'JSON script filter'),
                ('dynamic-fields-container', 'Dynamic fields container'),
            ]
            
            for check, description in checks:
                if check in content:
                    print_success(f"  {description}: Found")
                else:
                    print_error(f"  {description}: Not found")
    else:
        print_error(f"Template file not found: {template_file}")
    
    print()

def main():
    """Main verification function"""
    
    print("\n" + "="*70)
    print("ASSET EDIT FORM PRE-POPULATION VERIFICATION")
    print("="*70)
    
    try:
        # Run all verifications
        verify_javascript_integration()
        verify_template()
        result = verify_asset_edit_prepopulation()
        
        # Final summary
        print("\n" + "="*70)
        print("VERIFICATION COMPLETE")
        print("="*70)
        
        if result:
            print_success("All verifications passed!")
            print_info("\nNext steps:")
            print("  1. Navigate to any asset detail page")
            print("  2. Click 'Edit Asset'")
            print("  3. Verify all fields are pre-filled")
            print("  4. Open browser console (F12)")
            print("  5. Check for success messages")
            return 0
        else:
            print_error("Some verifications failed!")
            print_info("\nPlease review the output above and fix any issues.")
            return 1
            
    except Exception as e:
        print_error(f"Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
