import uuid

from django.conf import settings
from django.db import models


class ExternalCustomerSyncConfig(models.Model):
    class SyncStatus(models.TextChoices):
        NEVER = 'never', 'Never synced'
        SUCCESS = 'success', 'Success'
        PARTIAL = 'partial', 'Partial success'
        FAILED = 'failed', 'Failed'

    company = models.OneToOneField(
        'tenancy.Company',
        on_delete=models.CASCADE,
        related_name='external_customer_sync_config',
    )
    source_base_url = models.URLField()
    source_tenant_slug = models.CharField(max_length=80)
    api_token = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(
        max_length=16,
        choices=SyncStatus.choices,
        default=SyncStatus.NEVER,
    )
    last_error_message = models.TextField(blank=True)
    last_success_count = models.PositiveIntegerField(default=0)
    last_failure_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company__name']

    def __str__(self):
        return f'Customer sync config for {self.company}'


class ExternalCustomerReference(models.Model):
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', 'Synced'
        FAILED = 'failed', 'Failed'

    company = models.ForeignKey(
        'tenancy.Company',
        on_delete=models.CASCADE,
        related_name='external_customer_references',
    )
    external_uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    customer_status = models.CharField(max_length=32)
    customer_type = models.CharField(max_length=32)
    source_created_at = models.DateTimeField()
    last_synced_at = models.DateTimeField()
    sync_status = models.CharField(
        max_length=16,
        choices=SyncStatus.choices,
        default=SyncStatus.SYNCED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'external_uuid'],
                name='unique_external_customer_per_company',
            ),
        ]
        indexes = [
            models.Index(fields=['company', 'full_name'], name='extcust_company_name'),
            models.Index(fields=['company', 'phone'], name='extcust_company_phone'),
            models.Index(fields=['company', 'email'], name='extcust_company_email'),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.external_uuid})'


class CustomerSyncRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        PARTIAL = 'partial', 'Partial success'
        FAILED = 'failed', 'Failed'

    company = models.ForeignKey(
        'tenancy.Company',
        on_delete=models.CASCADE,
        related_name='customer_sync_runs',
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='customer_sync_runs',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_skipped = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['company', 'started_at'], name='custsync_company_started'),
        ]

    def __str__(self):
        return f'{self.company} sync at {self.started_at:%Y-%m-%d %H:%M:%S}'

