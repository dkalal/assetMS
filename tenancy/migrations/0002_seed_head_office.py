from __future__ import annotations

from django.db import migrations


def create_head_office_branches(apps, schema_editor):
    Company = apps.get_model('tenancy', 'Company')
    Branch = apps.get_model('tenancy', 'Branch')

    for company in Company.objects.all():
        defaults = {
            'name': 'Head Office',
            'address': company.address or '',
            'is_head_office': True,
            'metadata': {'system_seeded': True},
        }
        branch, created = Branch.objects.get_or_create(
            company=company,
            code='HEAD',
            defaults=defaults,
        )
        if not created:
            updated = False
            if not branch.is_head_office:
                branch.is_head_office = True
                updated = True
            if not branch.metadata:
                branch.metadata = {}
            if not branch.metadata.get('system_seeded'):
                branch.metadata['system_seeded'] = True
                updated = True
            if updated:
                branch.save(update_fields=['is_head_office', 'metadata'])


def remove_head_office_branches(apps, schema_editor):
    Branch = apps.get_model('tenancy', 'Branch')
    Branch.objects.filter(metadata__system_seeded=True, code='HEAD').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_head_office_branches, remove_head_office_branches),
    ]
