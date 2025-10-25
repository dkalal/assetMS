from __future__ import annotations

from django.db import migrations


def assign_users_to_head_office(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Company = apps.get_model('tenancy', 'Company')
    Branch = apps.get_model('tenancy', 'Branch')
    UserBranch = apps.get_model('tenancy', 'UserBranch')

    companies = list(Company.objects.all())
    branches_by_company = {
        company.pk: Branch.objects.filter(company=company, code='HEAD').first()
        for company in companies
    }

    for user in User.objects.select_related('company'):
        company_id = getattr(user, 'company_id', None)
        if not company_id:
            continue
        branch = branches_by_company.get(company_id)
        if not branch:
            continue
        membership, created = UserBranch.objects.get_or_create(
            user=user,
            company_id=company_id,
            branch=branch,
            defaults={'is_primary': True},
        )
        if not created and not membership.is_primary:
            membership.is_primary = True
            membership.save(update_fields=['is_primary'])


def remove_seeded_user_branches(apps, schema_editor):
    UserBranch = apps.get_model('tenancy', 'UserBranch')
    UserBranch.objects.filter(branch__code='HEAD', branch__metadata__system_seeded=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_user_company'),
        ('tenancy', '0002_seed_head_office'),
    ]

    operations = [
        migrations.RunPython(assign_users_to_head_office, remove_seeded_user_branches),
    ]
