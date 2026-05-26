from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tenancy', '0011_alter_approvalrequest_request_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalCustomerSyncConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_base_url', models.URLField()),
                ('source_tenant_slug', models.CharField(max_length=80)),
                ('api_token', models.CharField(max_length=255)),
                ('is_enabled', models.BooleanField(default=True)),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
                ('last_sync_status', models.CharField(choices=[('never', 'Never synced'), ('success', 'Success'), ('partial', 'Partial success'), ('failed', 'Failed')], default='never', max_length=16)),
                ('last_error_message', models.TextField(blank=True)),
                ('last_success_count', models.PositiveIntegerField(default=0)),
                ('last_failure_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='external_customer_sync_config', to='tenancy.company')),
            ],
            options={'ordering': ['company__name']},
        ),
        migrations.CreateModel(
            name='ExternalCustomerReference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('full_name', models.CharField(max_length=200)),
                ('phone', models.CharField(blank=True, max_length=32)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('customer_status', models.CharField(max_length=32)),
                ('customer_type', models.CharField(max_length=32)),
                ('source_created_at', models.DateTimeField()),
                ('last_synced_at', models.DateTimeField()),
                ('sync_status', models.CharField(choices=[('synced', 'Synced'), ('failed', 'Failed')], default='synced', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='external_customer_references', to='tenancy.company')),
            ],
            options={'ordering': ['full_name']},
        ),
        migrations.CreateModel(
            name='CustomerSyncRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('running', 'Running'), ('success', 'Success'), ('partial', 'Partial success'), ('failed', 'Failed')], default='running', max_length=16)),
                ('records_created', models.PositiveIntegerField(default=0)),
                ('records_updated', models.PositiveIntegerField(default=0)),
                ('records_skipped', models.PositiveIntegerField(default=0)),
                ('records_failed', models.PositiveIntegerField(default=0)),
                ('error_summary', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customer_sync_runs', to='tenancy.company')),
                ('initiated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='customer_sync_runs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-started_at']},
        ),
        migrations.AddIndex(
            model_name='customersyncrun',
            index=models.Index(fields=['company', 'started_at'], name='custsync_company_started'),
        ),
        migrations.AddConstraint(
            model_name='externalcustomerreference',
            constraint=models.UniqueConstraint(fields=('company', 'external_uuid'), name='unique_external_customer_per_company'),
        ),
        migrations.AddIndex(
            model_name='externalcustomerreference',
            index=models.Index(fields=['company', 'full_name'], name='extcust_company_name'),
        ),
        migrations.AddIndex(
            model_name='externalcustomerreference',
            index=models.Index(fields=['company', 'phone'], name='extcust_company_phone'),
        ),
        migrations.AddIndex(
            model_name='externalcustomerreference',
            index=models.Index(fields=['company', 'email'], name='extcust_company_email'),
        ),
    ]
