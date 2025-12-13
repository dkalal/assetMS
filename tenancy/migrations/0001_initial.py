from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


def seed_default_company(apps, schema_editor):
    Company = apps.get_model('tenancy', 'Company')
    OrganizationProfile = apps.get_model('settings', 'OrganizationProfile')
    profile = None
    if OrganizationProfile:
        profile = OrganizationProfile.objects.first()

    if profile:
        Company.objects.create(
            name=profile.name,
            address="\n".join(filter(None, [
                profile.address_line1,
                profile.address_line2,
                ", ".join(filter(None, [profile.city, profile.state, profile.postal_code])),
                profile.country,
            ])),
            tax_id=profile.tax_id,
            contact_person=profile.legal_name or '',
            phone=profile.phone,
            email=profile.email,
            timezone=profile.timezone,
            metadata={
                'registration_number': profile.registration_number,
                'industry': profile.industry,
                'currency': profile.currency,
                'date_format': profile.date_format,
            },
        )
    else:
        Company.objects.create(
            name='Default Company',
            email='admin@example.com',
            timezone='UTC',
        )


def reverse_seed_default_company(apps, schema_editor):
    Company = apps.get_model('tenancy', 'Company')
    Company.objects.all().delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('settings', '0003_organizationprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('address', models.TextField(blank=True)),
                ('tax_id', models.CharField(blank=True, max_length=100)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='company/logos/')),
                ('contact_person', models.CharField(blank=True, max_length=255)),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('timezone', models.CharField(default='UTC', max_length=64)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'Companies',
            },
        ),
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('address', models.TextField(blank=True)),
                ('code', models.CharField(max_length=50)),
                ('is_head_office', models.BooleanField(default=False)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='branches', to='tenancy.company')),
            ],
            options={
                'ordering': ['company__name', 'name'],
                'unique_together': {('company', 'code')},
            },
        ),
        migrations.CreateModel(
            name='UserBranch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_primary', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='tenancy.branch')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_branches', to='tenancy.company')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_branches', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'branch')},
            },
        ),
        migrations.AddConstraint(
            model_name='branch',
            constraint=models.UniqueConstraint(condition=Q(is_head_office=True), fields=('company',), name='unique_head_office_per_company'),
        ),
        migrations.AddConstraint(
            model_name='userbranch',
            constraint=models.UniqueConstraint(condition=Q(is_primary=True), fields=('user', 'company'), name='unique_primary_branch_per_user_company'),
        ),
        migrations.RunPython(seed_default_company, reverse_seed_default_company),
    ]
