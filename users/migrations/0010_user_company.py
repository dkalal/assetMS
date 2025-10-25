from __future__ import annotations

from django.db import migrations, models


def assign_company_to_users(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Company = apps.get_model('tenancy', 'Company')
    company = Company.objects.order_by('id').first()
    if not company:
        return
    User.objects.filter(company__isnull=True).update(company=company)


def remove_company_from_users(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.update(company=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0001_initial'),
        ('users', '0009_rolepermissionmatrix'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='users', to='tenancy.company'),
        ),
        migrations.RunPython(assign_company_to_users, remove_company_from_users),
    ]
