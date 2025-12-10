# Generated migration to normalize asset status values

from django.db import migrations


def normalize_status_values(apps, schema_editor):
    """
    Normalize asset status values to use consistent constants
    """
    Asset = apps.get_model('assets', 'Asset')
    
    # Map old status values to new constants
    status_mapping = {
        'active': 'active',
        'in_maintenance': 'in_maintenance',
        'retired': 'retired',
        'lost': 'lost',
        'deleted': 'deleted',
        'transferred': 'transferred',
    }
    
    # Update any assets with non-standard status values
    for old_status, new_status in status_mapping.items():
        Asset.objects.filter(status=old_status).update(status=new_status)


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(normalize_status_values, migrations.RunPython.noop),
    ]
