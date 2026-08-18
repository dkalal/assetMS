import json
import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.generic import DetailView, ListView
from django.views.decorators.http import require_GET, require_POST

from users.decorators import api_admin_required
from tenancy.mixins import CompanyRequiredMixin

from .models import CustomerSyncRun, ExternalCustomerSyncConfig
from .models import ExternalCustomerReference
from .services import (
    CustomerSyncService,
    SourceCustomerApiError,
    get_sync_timeout_seconds,
    normalize_source_base_url,
)


class SyncedCustomerListView(LoginRequiredMixin, CompanyRequiredMixin, ListView):
    template_name = 'integrations/synced_customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            ExternalCustomerReference.objects.filter(company=self.request.company)
            .annotate(asset_count=Count('assets', distinct=True))
            .order_by('full_name')
        )
        search = (self.request.GET.get('search') or '').strip()
        sync_status = (self.request.GET.get('sync_status') or '').strip()
        if search:
            search_filter = (
                Q(full_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )
            try:
                search_filter |= Q(external_uuid=uuid.UUID(search))
            except (ValueError, TypeError):
                pass
            queryset = queryset.filter(search_filter)
        if sync_status:
            queryset = queryset.filter(sync_status=sync_status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['search'] = (self.request.GET.get('search') or '').strip()
        context['sync_status'] = (self.request.GET.get('sync_status') or '').strip()
        context['summary'] = {
            'total': queryset.count(),
            'synced': queryset.filter(sync_status=ExternalCustomerReference.SyncStatus.SYNCED).count(),
            'failed': queryset.filter(sync_status=ExternalCustomerReference.SyncStatus.FAILED).count(),
            'linked': queryset.filter(asset_count__gt=0).count(),
        }
        context['status_choices'] = ExternalCustomerReference.SyncStatus.choices
        return context


class SyncedCustomerDetailView(LoginRequiredMixin, CompanyRequiredMixin, DetailView):
    template_name = 'integrations/synced_customer_detail.html'
    context_object_name = 'customer'
    slug_field = 'external_uuid'
    slug_url_kwarg = 'external_uuid'

    def get_queryset(self):
        return (
            ExternalCustomerReference.objects.filter(company=self.request.company)
            .annotate(asset_count=Count('assets', distinct=True))
            .prefetch_related('assets__category', 'assets__branch')
            .order_by('full_name')
        )


def _config_payload(config):
    return {
        'is_configured': config is not None,
        'source_base_url': config.source_base_url if config else '',
        'source_tenant_slug': config.source_tenant_slug if config else '',
        'is_enabled': config.is_enabled if config else False,
        'last_synced_at': config.last_synced_at.isoformat() if config and config.last_synced_at else None,
        'last_sync_status': config.last_sync_status if config else 'never',
        'last_error_message': config.last_error_message if config else '',
        'last_success_count': config.last_success_count if config else 0,
        'last_failure_count': config.last_failure_count if config else 0,
        'timeout_seconds': get_sync_timeout_seconds(),
    }


@api_admin_required
@require_GET
def customer_sync_config(request):
    config = ExternalCustomerSyncConfig.objects.filter(company=request.company).first()
    latest_run = CustomerSyncRun.objects.filter(company=request.company).first()
    payload = _config_payload(config)
    payload['latest_run'] = (
        {
            'started_at': latest_run.started_at.isoformat(),
            'finished_at': latest_run.finished_at.isoformat() if latest_run.finished_at else None,
            'status': latest_run.status,
            'records_created': latest_run.records_created,
            'records_updated': latest_run.records_updated,
            'records_skipped': latest_run.records_skipped,
            'records_failed': latest_run.records_failed,
            'error_summary': latest_run.error_summary,
        }
        if latest_run
        else None
    )
    return JsonResponse({'success': True, 'config': payload})


@api_admin_required
@require_POST
def customer_sync_config_update(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload.'}, status=400)

    source_base_url = normalize_source_base_url(data.get('source_base_url') or '')
    source_tenant_slug = (data.get('source_tenant_slug') or '').strip()
    api_token = (data.get('api_token') or '').strip()
    is_enabled = bool(data.get('is_enabled', True))

    existing = ExternalCustomerSyncConfig.objects.filter(company=request.company).first()
    if existing and not api_token:
        api_token = existing.api_token

    if not source_base_url or not source_tenant_slug or not api_token:
        return JsonResponse({'success': False, 'error': 'Base URL, tenant slug, and API token are required.'}, status=400)

    config, _ = ExternalCustomerSyncConfig.objects.update_or_create(
        company=request.company,
        defaults={
            'source_base_url': source_base_url,
            'source_tenant_slug': source_tenant_slug,
            'api_token': api_token,
            'is_enabled': is_enabled,
        },
    )

    return JsonResponse({'success': True, 'config': _config_payload(config)})


@api_admin_required
@require_POST
def run_customer_sync(request):
    try:
        outcome = CustomerSyncService.sync_company_customers(
            company=request.company,
            initiated_by=request.user,
        )
    except SourceCustomerApiError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)

    return JsonResponse(
        {
            'success': True,
            'sync': {
                'status': outcome.status,
                'created': outcome.created,
                'updated': outcome.updated,
                'skipped': outcome.skipped,
                'failed': outcome.failed,
                'error_summary': outcome.error_summary,
                'finished_at': outcome.run.finished_at.isoformat() if outcome.run.finished_at else None,
            },
        }
    )
