# Generated migration to remove depreciation fields
# This migration removes all depreciation-related fields from the Asset model
# as they are not needed for the core asset management functionality

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0021_intelligent_duplicate_detection'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='asset',
            name='purchase_value',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='purchase_date',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='depreciation_method',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='useful_life_years',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='salvage_value',
        ),
    ]
