#!/usr/bin/env python
"""
Approval Workflow Diagnostic Script

Run this script to diagnose issues with approval workflows.

Usage:
    python diagnose_approval.py <request_id>

Example:
    python diagnose_approval.py 4
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from tenancy.approval_models import ApprovalRequest
from assets.models import Asset, AssetCategory, AssetCategoryField
from tenancy.models import Branch
from django.contrib.auth import get_user_model

User = get_user_model()


def diagnose_request(request_id):
    """Diagnose an approval request."""
    print("=" * 70)
    print(f"APPROVAL REQUEST DIAGNOSTIC - Request #{request_id}")
    print("=" * 70)
    print()
    
    try:
        req = ApprovalRequest.objects.get(pk=request_id)
    except ApprovalRequest.DoesNotExist:
        print(f"❌ ERROR: Request #{request_id} not found!")
        return
    
    # Basic Info
    print("📋 BASIC INFORMATION")
    print("-" * 70)
    print(f"Title: {req.title}")
    print(f"Type: {req.get_request_type_display()}")
    print(f"Status: {req.get_status_display()}")
    print(f"Priority: {req.get_priority_display()}")
    print(f"Company: {req.company.name}")
    print(f"Branch: {req.branch.name}")
    print(f"Requested by: {req.requested_by.username} ({req.requested_by.get_full_name()})")
    print(f"Assigned to: {req.assigned_to.username if req.assigned_to else 'Not assigned'}")
    print(f"Created: {req.created_at}")
    print(f"Updated: {req.updated_at}")
    print()
    
    # Approval Status
    if req.status == 'approved':
        print("✅ APPROVAL STATUS")
        print("-" * 70)
        print(f"Approved by: {req.approved_by.username if req.approved_by else 'N/A'}")
        print(f"Approved at: {req.approved_at}")
        print()
    
    # Metadata
    print("📦 METADATA")
    print("-" * 70)
    import json
    print(json.dumps(req.metadata, indent=2))
    print()
    
    # Asset Creation Specific Checks
    if req.request_type == 'asset_creation':
        print("🔍 ASSET CREATION CHECKS")
        print("-" * 70)
        
        asset_data = req.metadata.get('asset_data', {})
        
        # Check category
        category_id = asset_data.get('category_id')
        if category_id:
            try:
                category = AssetCategory.objects.get(pk=category_id)
                print(f"✅ Category: {category.name} (ID: {category_id})")
            except AssetCategory.DoesNotExist:
                print(f"❌ Category ID {category_id} NOT FOUND!")
        else:
            print("❌ No category_id in metadata!")
        
        # Check branch
        branch_id = asset_data.get('branch_id')
        if branch_id:
            try:
                branch = Branch.objects.get(pk=branch_id)
                print(f"✅ Branch: {branch.name} (ID: {branch_id})")
            except Branch.DoesNotExist:
                print(f"❌ Branch ID {branch_id} NOT FOUND!")
        else:
            print("❌ No branch_id in metadata!")
        
        # Check required fields
        if category_id:
            try:
                category = AssetCategory.objects.get(pk=category_id)
                required_fields = AssetCategoryField.objects.filter(
                    category=category,
                    required=True
                )
                
                if required_fields.exists():
                    print(f"\n📝 Required Fields Check:")
                    dynamic_data = asset_data.get('dynamic_data', {})
                    
                    for field in required_fields:
                        value = dynamic_data.get(field.key)
                        if value:
                            print(f"  ✅ {field.label} ({field.key}): {value}")
                        else:
                            print(f"  ❌ {field.label} ({field.key}): MISSING!")
                else:
                    print("\nℹ️  No required fields for this category")
            except Exception as e:
                print(f"\n❌ Error checking required fields: {e}")
        
        # Check if asset was created
        created_asset_id = req.metadata.get('created_asset_id')
        if created_asset_id:
            try:
                asset = Asset.objects.get(pk=created_asset_id)
                print(f"\n✅ ASSET CREATED!")
                print(f"   Asset ID: {asset.id}")
                print(f"   Asset UUID: {asset.uuid}")
                print(f"   Asset Name: {asset}")
                print(f"   Status: {asset.status}")
                print(f"   QR Code: {'Yes' if asset.qr_code else 'No'}")
            except Asset.DoesNotExist:
                print(f"\n⚠️  Asset ID {created_asset_id} in metadata but NOT FOUND in database!")
        else:
            if req.status == 'approved':
                print(f"\n❌ Request approved but NO ASSET CREATED!")
                print(f"   This indicates asset creation failed.")
            else:
                print(f"\nℹ️  Asset not yet created (request not approved)")
        
        print()
    
    # Asset Disposal Specific Checks
    elif req.request_type == 'asset_disposal':
        print("🗑️  ASSET DISPOSAL CHECKS")
        print("-" * 70)
        
        asset_id = req.metadata.get('asset_id')
        if asset_id:
            try:
                asset = Asset.objects.get(pk=asset_id)
                print(f"✅ Asset: {asset} (ID: {asset_id})")
                print(f"   Status: {asset.status}")
                print(f"   Active: {asset.is_active}")
                print(f"   Disposal Method: {req.metadata.get('disposal_method', 'N/A')}")
                print(f"   Disposal Reason: {req.metadata.get('disposal_reason', 'N/A')}")
            except Asset.DoesNotExist:
                print(f"❌ Asset ID {asset_id} NOT FOUND!")
        else:
            print("❌ No asset_id in metadata!")
        
        print()
    
    # Recommendations
    print("💡 RECOMMENDATIONS")
    print("-" * 70)
    
    if req.status == 'pending':
        print("• Request is pending approval")
        print("• Admin should review and approve/reject")
    elif req.status == 'approved' and req.request_type == 'asset_creation':
        created_asset_id = req.metadata.get('created_asset_id')
        if not created_asset_id:
            print("❌ ISSUE: Request approved but asset not created!")
            print("\nTroubleshooting steps:")
            print("1. Check Django logs for errors")
            print("2. Verify category and branch exist")
            print("3. Verify all required fields are present")
            print("4. Try creating asset manually:")
            print(f"\n   python manage.py shell")
            print(f"   >>> from tenancy.approval_models import ApprovalRequest")
            print(f"   >>> req = ApprovalRequest.objects.get(pk={request_id})")
            print(f"   >>> asset = req.create_asset_from_approval()")
            print(f"   >>> print(asset)")
        else:
            print("✅ Everything looks good!")
    elif req.status == 'rejected':
        print(f"• Request was rejected")
        print(f"• Reason: {req.rejection_reason}")
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diagnose_approval.py <request_id>")
        print("Example: python diagnose_approval.py 4")
        sys.exit(1)
    
    try:
        request_id = int(sys.argv[1])
        diagnose_request(request_id)
    except ValueError:
        print("Error: request_id must be a number")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
