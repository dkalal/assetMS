# Generated migration for normalizing category field keys

from django.db import migrations
import re


def normalize_field_keys(apps, schema_editor):
    """
    Normalize all AssetCategoryField keys to ensure they follow the pattern:
    ^[a-z][a-z0-9_]*$
    
    For legacy fields without proper keys, generate them from labels.
    """
    AssetCategoryField = apps.get_model('assets', 'AssetCategoryField')
    
    def generate_key_from_label(label):
        """Generate a valid key from a label."""
        # Convert to lowercase
        key = label.lower()
        # Replace spaces and hyphens with underscores
        key = re.sub(r'[\s\-]+', '_', key)
        # Remove all non-alphanumeric characters except underscores
        key = re.sub(r'[^a-z0-9_]', '', key)
        # Ensure it starts with a letter
        if key and not key[0].isalpha():
            key = 'field_' + key
        # Ensure it's not empty
        if not key:
            key = 'custom_field'
        return key
    
    fields_updated = 0
    fields_with_issues = []
    
    for field in AssetCategoryField.objects.all():
        original_key = field.key
        needs_update = False
        
        # Check if key is empty or None
        if not field.key or not field.key.strip():
            field.key = generate_key_from_label(field.label)
            needs_update = True
            fields_with_issues.append({
                'id': field.id,
                'category': field.category.name if field.category else 'Unknown',
                'label': field.label,
                'old_key': original_key,
                'new_key': field.key,
                'reason': 'Empty key'
            })
        
        # Check if key doesn't match pattern
        elif not re.match(r'^[a-z][a-z0-9_]*$', field.key):
            new_key = generate_key_from_label(field.key)
            fields_with_issues.append({
                'id': field.id,
                'category': field.category.name if field.category else 'Unknown',
                'label': field.label,
                'old_key': original_key,
                'new_key': new_key,
                'reason': 'Invalid pattern'
            })
            field.key = new_key
            needs_update = True
        
        # Handle duplicate keys within the same category
        if needs_update:
            # Check for duplicates
            counter = 1
            base_key = field.key
            while AssetCategoryField.objects.filter(
                category=field.category,
                key=field.key
            ).exclude(id=field.id).exists():
                field.key = f"{base_key}_{counter}"
                counter += 1
            
            field.save(update_fields=['key'])
            fields_updated += 1
    
    # Print summary
    if fields_updated > 0:
        print(f"\n{'='*80}")
        print(f"CATEGORY FIELD KEY NORMALIZATION COMPLETE")
        print(f"{'='*80}")
        print(f"Total fields updated: {fields_updated}")
        print(f"\nDetails:")
        for issue in fields_with_issues:
            print(f"\n  Field ID: {issue['id']}")
            print(f"  Category: {issue['category']}")
            print(f"  Label: {issue['label']}")
            print(f"  Old Key: '{issue['old_key']}'")
            print(f"  New Key: '{issue['new_key']}'")
            print(f"  Reason: {issue['reason']}")
        print(f"\n{'='*80}\n")
    else:
        print("\nNo category field keys needed normalization.")


def reverse_migration(apps, schema_editor):
    """
    This migration cannot be reversed as we don't store the original invalid keys.
    """
    print("WARNING: This migration cannot be reversed. Original keys were invalid.")


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0016_normalize_asset_status'),  # Update to your latest migration
    ]

    operations = [
        migrations.RunPython(normalize_field_keys, reverse_migration),
    ]
