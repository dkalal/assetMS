# Generated migration to fix assets stuck in 'transferred' status
# This fixes the bug where completed transfers left assets in 'transferred' status
# instead of restoring them to 'active' status

from django.db import migrations


def fix_transferred_assets(apps, schema_editor):
    """
    WORLD-CLASS FIX: Restore assets stuck in 'transferred' status to 'active'.
    
    When a transfer completes, the asset should be ACTIVE and ready for use by the new owner.
    The 'transferred' status is temporary during the transfer process only.
    
    This migration fixes existing data where assets were incorrectly left in 'transferred'
    status after transfer completion.
    
    Inspired by ServiceNow ITAM, IBM Maximo, SAP EAM transfer workflows.
    """
    Asset = apps.get_model('assets', 'Asset')
    AssetTransfer = apps.get_model('assets', 'AssetTransfer')
    
    # Find all assets currently in 'transferred' status
    transferred_assets = Asset.objects.filter(status='transferred')
    
    fixed_count = 0
    for asset in transferred_assets:
        # Check if asset has a completed transfer
        completed_transfer = AssetTransfer.objects.filter(
            asset=asset,
            state='completed'
        ).order_by('-updated_at').first()
        
        # Check if asset has any active (pending) transfers
        has_active_transfer = AssetTransfer.objects.filter(
            asset=asset,
            state__in=['pending_receiver', 'receiver_approved', 'awaiting_admin']
        ).exists()
        
        # If transfer is completed OR no active transfer exists, restore to active
        if completed_transfer or not has_active_transfer:
            asset.status = 'active'
            asset.save(update_fields=['status'])
            fixed_count += 1
            
            if completed_transfer:
                print(f"  [OK] Asset {asset.pk} restored to active (transfer completed)")
            else:
                print(f"  [OK] Asset {asset.pk} restored to active (no active transfer)")
    
    if fixed_count > 0:
        print(f"\n[OK] Fixed {fixed_count} assets stuck in 'transferred' status")
    else:
        print("\n[OK] No assets needed fixing - all statuses are correct")


def reverse_fix(apps, schema_editor):
    """
    Reverse migration - not recommended as it would reintroduce the bug.
    This is a no-op to prevent accidental reversal.
    """
    print("[WARNING] Reverse migration skipped - status fix is required for system integrity")


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0016_normalize_asset_status'),  # Previous migration
    ]

    operations = [
        migrations.RunPython(fix_transferred_assets, reverse_fix),
    ]
