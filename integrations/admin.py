from django.contrib import admin

from .models import CustomerSyncRun, ExternalCustomerReference, ExternalCustomerSyncConfig


@admin.register(ExternalCustomerSyncConfig)
class ExternalCustomerSyncConfigAdmin(admin.ModelAdmin):
    list_display = ('company', 'source_tenant_slug', 'is_enabled', 'last_sync_status', 'last_synced_at')
    list_filter = ('is_enabled', 'last_sync_status')
    search_fields = ('company__name', 'source_tenant_slug', 'source_base_url')


@admin.register(ExternalCustomerReference)
class ExternalCustomerReferenceAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'company', 'phone', 'email', 'customer_status', 'last_synced_at')
    list_filter = ('company', 'customer_status', 'customer_type')
    search_fields = ('full_name', 'phone', 'email', 'external_uuid')


@admin.register(CustomerSyncRun)
class CustomerSyncRunAdmin(admin.ModelAdmin):
    list_display = ('company', 'initiated_by', 'status', 'started_at', 'finished_at')
    list_filter = ('status', 'company')
    search_fields = ('company__name', 'initiated_by__username', 'error_summary')
