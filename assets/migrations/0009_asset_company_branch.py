from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


def assign_asset_company(apps, schema_editor):
    Asset = apps.get_model('assets', 'Asset')
    Company = apps.get_model('tenancy', 'Company')
    company = Company.objects.order_by('id').first()
    if not company:
        return
    Asset.objects.filter(company__isnull=True).update(company=company)


def remove_asset_company(apps, schema_editor):
    Asset = apps.get_model('assets', 'Asset')
    Asset.objects.update(company=None, branch=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0001_initial'),
        ('assets', '0008_asset_depreciation_method_asset_purchase_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets', to='tenancy.branch'),
        ),
        migrations.AddField(
            model_name='asset',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assets', to='tenancy.company'),
        ),
        migrations.AlterField(
            model_name='asset',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('in_maintenance', 'In Maintenance'), ('retired', 'Retired'), ('lost', 'Lost'), ('deleted', 'Deleted'), ('transferred', 'Transferred')], default='active', max_length=20),
        ),
        migrations.RunPython(assign_asset_company, remove_asset_company),
        migrations.AlterField(
            model_name='asset',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets', to='tenancy.company'),
        ),
    ]
