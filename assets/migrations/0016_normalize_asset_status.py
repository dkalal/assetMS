# Generated migration to normalize asset status values to lowercase
# This fixes the critical bug where assets have capitalized status values
# causing validation failures in maintenance operations

from django.db import migrations


def normalize_asset_statuses(apps, schema_editor):
    """
    WORLD-CLASS FIX: Normalize all asset status values to lowercase.
    
    This migration fixes existing data where status values were saved as
    capitalized (e.g., "Active", "In Maintenance") instead of lowercase
    (e.g., "active", "in_maintenance").
    
    Inspired by ServiceNow ITAM, IBM Maximo, SAP EAM data normalization best practices.
    """
    Asset = apps.get_model('assets', 'Asset')
    
    # Status mapping: Display value → Database value
    status_mapping = {
        'Active': 'active',
        'active': 'active',
        'In Maintenance': 'in_maintenance',
        'in_maintenance': 'in_maintenance',
        'Retired': 'retired',
        'retired': 'retired',
        'Lost': 'lost',
        'lost': 'lost',
        'Deleted': 'deleted',
        'deleted': 'deleted',
        'Transferred': 'transferred',
        'transferred': 'transferred',
    }
    
    # Get all assets with non-normalized status
    assets_to_fix = Asset.objects.all()
    
    fixed_count = 0
    for asset in assets_to_fix:
        if asset.status in status_mapping:
            normalized_status = status_mapping[asset.status]
            if asset.status != normalized_status:
                asset.status = normalized_status
                asset.save(update_fields=['status'])
                fixed_count += 1
    
    print(f"✅ Normalized {fixed_count} asset status values to lowercase")


def reverse_normalize(apps, schema_editor):
    """
    Reverse migration - not recommended as it would break the system.
    This is a no-op to prevent accidental reversal.
    """
    print("⚠️ Reverse migration skipped - status normalization is required for system integrity")


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0015_add_filters_to_exportlog'),  # Latest migration
        ('assets', '0002_add_status_change_tracking'),  # Merge with status tracking
    ]

    operations = [
        migrations.RunPython(normalize_asset_statuses, reverse_normalize),
    ]
