import json
import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Prefetch
from django.http import JsonResponse
from django.views.generic import DetailView, ListView
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from users.decorators import (
    api_admin_required,
    require_customer_permission,
    require_transfer_permission,
    require_maintenance_permission,
    _has_permission,
    _is_admin,
)
from tenancy.mixins import CompanyRequiredMixin
from audit.utils import log_audit

from .models import (
    CustomerNote,
    CustomerSyncRun,
    ExternalCustomerSyncConfig,
    ExternalCustomerReference,
)
from .services import (
    CustomerSyncService,
    SourceCustomerApiError,
    get_sync_timeout_seconds,
    normalize_source_base_url,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _customer_branch_qs(request):
    """
    Return the base ExternalCustomerReference queryset scoped to the request.

    - Admins: all customers in the company.
    - Managers/users with can_manage_customers: customers whose branch matches
      any branch the user is a member of (via UserBranch). Users without an
      active branch membership have no customer access.
    """
    company = request.company
    user = request.user
    qs = ExternalCustomerReference.objects.filter(company=company)

    if _is_admin(user):
        return qs

    from tenancy.models import UserBranch
    user_branch_ids = list(
        UserBranch.objects.filter(user=user, company=company, branch__is_active=True)
        .values_list('branch_id', flat=True)
    )
    if not user_branch_ids:
        return qs.none()

    # Customers assigned to one of the user's branches OR unassigned (null branch)
    return qs.filter(Q(branch_id__in=user_branch_ids) | Q(branch__isnull=True))


def _get_user_branch_ids(request):
    """Return list of branch PKs the requesting user belongs to."""
    from tenancy.models import UserBranch
    return list(
        UserBranch.objects.filter(
            user=request.user,
            company=request.company,
            branch__is_active=True,
        ).values_list('branch_id', flat=True)
    )


# ---------------------------------------------------------------------------
# Customer List & Detail (existing views — enhanced)
# ---------------------------------------------------------------------------

class SyncedCustomerListView(LoginRequiredMixin, CompanyRequiredMixin, ListView):
    template_name = 'integrations/synced_customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not _has_permission(request.user, 'can_manage_customers'):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('Customer management permission required.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            _customer_branch_qs(self.request)
            .select_related('branch')
            .annotate(asset_count=Count('assets', distinct=True))
            .order_by('full_name')
        )
        search = (self.request.GET.get('search') or '').strip()
        sync_status = (self.request.GET.get('sync_status') or '').strip()
        branch_filter = (self.request.GET.get('branch') or '').strip()

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
        if branch_filter:
            queryset = queryset.filter(branch_id=branch_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = _customer_branch_qs(self.request).annotate(asset_count=Count('assets', distinct=True))
        context['search'] = (self.request.GET.get('search') or '').strip()
        context['sync_status'] = (self.request.GET.get('sync_status') or '').strip()
        context['branch_filter'] = (self.request.GET.get('branch') or '').strip()
        context['summary'] = {
            'total': base_qs.count(),
            'synced': base_qs.filter(sync_status=ExternalCustomerReference.SyncStatus.SYNCED).count(),
            'failed': base_qs.filter(sync_status=ExternalCustomerReference.SyncStatus.FAILED).count(),
            'linked': base_qs.filter(asset_count__gt=0).count(),
        }
        context['status_choices'] = ExternalCustomerReference.SyncStatus.choices
        context['can_manage'] = _has_permission(self.request.user, 'can_manage_customers')
        context['is_admin'] = _is_admin(self.request.user)

        # Branch filter options
        from tenancy.models import Branch
        if _is_admin(self.request.user):
            context['branches'] = Branch.objects.filter(
                company=self.request.company, is_active=True
            ).order_by('name')
        else:
            from tenancy.models import UserBranch
            branch_ids = _get_user_branch_ids(self.request)
            context['branches'] = Branch.objects.filter(
                id__in=branch_ids, is_active=True
            ).order_by('name')
        return context


class SyncedCustomerDetailView(LoginRequiredMixin, CompanyRequiredMixin, DetailView):
    """Customer 360° view — assets, notes, maintenance, transfer history."""

    template_name = 'integrations/customer_360.html'
    context_object_name = 'customer'
    slug_field = 'external_uuid'
    slug_url_kwarg = 'external_uuid'

    def dispatch(self, request, *args, **kwargs):
        if not _has_permission(request.user, 'can_manage_customers'):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('Customer management permission required.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            _customer_branch_qs(self.request)
            .select_related('branch')
            .annotate(asset_count=Count('assets', distinct=True))
            .prefetch_related(
                Prefetch(
                    'assets',
                    queryset=__import__(
                        'assets.models', fromlist=['Asset']
                    ).Asset.objects.select_related('category', 'branch').order_by('-created_at'),
                ),
                Prefetch(
                    'notes',
                    queryset=CustomerNote.objects.select_related('author').order_by('-created_at'),
                ),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        company = self.request.company
        user = self.request.user

        # Maintenance records for this customer's assets
        from assets.models import MaintenanceRecord
        asset_ids = list(customer.assets.values_list('id', flat=True))
        maintenance_records = (
            MaintenanceRecord.objects.filter(asset_id__in=asset_ids, company=company)
            .select_related('asset', 'performed_by')
            .order_by('-scheduled_for')[:20]
        )

        # Transfer history for this customer's assets
        from assets.models import AssetTransfer
        transfers = (
            AssetTransfer.objects.filter(asset_id__in=asset_ids, company=company)
            .select_related('asset', 'from_user', 'to_user', 'from_branch', 'to_branch')
            .order_by('-created_at')[:20]
        )

        # Audit trail for this customer
        from audit.models import AuditLog
        audit_entries = (
            AuditLog.objects.filter(company=company, metadata__customer_id=customer.pk)
            .select_related('user')
            .order_by('-timestamp')[:30]
        )

        # Available assets for linking (branch-scoped, unlinked)
        from assets.models import Asset
        from tenancy.models import UserBranch
        if _is_admin(user):
            linkable_assets = Asset.objects.filter(
                company=company,
                customer_reference__isnull=True,
                status='active',
            ).select_related('category', 'branch').order_by('category__name')
        else:
            branch_ids = _get_user_branch_ids(self.request)
            linkable_assets = Asset.objects.filter(
                company=company,
                branch_id__in=branch_ids,
                customer_reference__isnull=True,
                status='active',
            ).select_related('category', 'branch').order_by('category__name')

        # Available branches for reassignment (admin only)
        from tenancy.models import Branch
        available_branches = (
            Branch.objects.filter(company=company, is_active=True).order_by('name')
            if _is_admin(user) else []
        )

        context.update({
            'maintenance_records': maintenance_records,
            'transfers': transfers,
            'audit_entries': audit_entries,
            'linkable_assets': linkable_assets,
            'available_branches': available_branches,
            'transfer_customers': (
                _customer_branch_qs(self.request)
                .exclude(pk=customer.pk)
                .only('external_uuid', 'full_name', 'phone', 'branch')
                .select_related('branch')
                .order_by('full_name')
            ) if _has_permission(user, 'can_transfer_assets') else [],
            'can_manage': _has_permission(user, 'can_manage_customers'),
            'can_transfer': _has_permission(user, 'can_transfer_assets'),
            'can_maintenance': _has_permission(user, 'can_schedule_maintenance'),
            'is_admin': _is_admin(user),
        })
        return context


# ---------------------------------------------------------------------------
# Customer Notes API
# ---------------------------------------------------------------------------

@require_customer_permission
@require_POST
def api_add_customer_note(request, external_uuid):
    """Add a threaded note to a customer record."""
    customer = _customer_branch_qs(request).filter(external_uuid=external_uuid).first()
    if not customer:
        return JsonResponse({'success': False, 'error': 'Customer not found.'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    body = (data.get('body') or '').strip()
    if not body:
        return JsonResponse({'success': False, 'error': 'Note body is required.'}, status=400)
    if len(body) > 2000:
        return JsonResponse({'success': False, 'error': 'Note must not exceed 2000 characters.'}, status=400)

    note = CustomerNote.objects.create(
        customer=customer,
        company=request.company,
        author=request.user,
        body=body,
    )

    log_audit(
        request.user,
        'customer_note_added',
        details=f'Note added to customer {customer.full_name}',
        company=request.company,
        metadata={'customer_id': customer.pk, 'note_id': note.pk},
    )

    return JsonResponse({
        'success': True,
        'note': {
            'id': note.pk,
            'body': note.body,
            'author': request.user.get_full_name() or request.user.username,
            'created_at': note.created_at.isoformat(),
        },
    })


@require_customer_permission
@require_POST
def api_delete_customer_note(request, note_id):
    """Delete own note (or any note if admin)."""
    qs = CustomerNote.objects.filter(pk=note_id, company=request.company)
    if not _is_admin(request.user):
        qs = qs.filter(author=request.user)
    note = qs.first()
    if not note:
        return JsonResponse({'success': False, 'error': 'Note not found.'}, status=404)

    customer_name = note.customer.full_name
    note.delete()

    log_audit(
        request.user,
        'customer_note_deleted',
        details=f'Note deleted from customer {customer_name}',
        company=request.company,
        metadata={'note_id': note_id},
    )
    return JsonResponse({'success': True})


# ---------------------------------------------------------------------------
# Asset Link / Unlink API
# ---------------------------------------------------------------------------

@require_customer_permission
@require_POST
def api_link_asset_to_customer(request, external_uuid):
    """Link an asset to a customer (branch-scoped), with optional note."""
    from assets.models import Asset
    from django.db import transaction

    customer = _customer_branch_qs(request).filter(external_uuid=external_uuid).first()
    if not customer:
        return JsonResponse({'success': False, 'error': 'Customer not found.'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    asset_id = data.get('asset_id')
    if not asset_id:
        return JsonResponse({'success': False, 'error': 'asset_id is required.'}, status=400)

    note_body = (data.get('note') or '').strip()
    if note_body and len(note_body) > 2000:
        return JsonResponse({'success': False, 'error': 'Note must not exceed 2000 characters.'}, status=400)

    # Branch-scope the asset lookup
    asset_qs = Asset.objects.filter(pk=asset_id, company=request.company)
    if not _is_admin(request.user):
        branch_ids = _get_user_branch_ids(request)
        asset_qs = asset_qs.filter(branch_id__in=branch_ids)

    asset = asset_qs.first()
    if not asset:
        return JsonResponse({'success': False, 'error': 'Asset not found or not in your branch.'}, status=404)

    if asset.customer_reference_id:
        return JsonResponse({'success': False, 'error': 'Asset is already linked to a customer.'}, status=400)

    with transaction.atomic():
        asset.customer_reference = customer
        asset.save(update_fields=['customer_reference', 'updated_at'])

        note_data = None
        if note_body:
            note = CustomerNote.objects.create(
                customer=customer,
                company=request.company,
                author=request.user,
                body=note_body,
            )
            note_data = {
                'id': note.pk,
                'body': note.body,
                'author': request.user.get_full_name() or request.user.username,
                'created_at': note.created_at.isoformat(),
            }

    log_audit(
        request.user,
        'customer_asset_linked',
        asset=asset,
        details=f'Asset linked to customer {customer.full_name}'
                + (f' with note' if note_body else ''),
        company=request.company,
        metadata={'customer_id': customer.pk, 'asset_id': asset.pk},
    )

    return JsonResponse({
        'success': True,
        'asset': {
            'id': asset.pk,
            'label': str(asset),
            'category': asset.category.name,
            'branch': asset.branch.name if asset.branch else '-',
            'status': asset.get_status_display(),
        },
        'note': note_data,
    })


@require_customer_permission
@require_POST
def api_unlink_asset_from_customer(request, external_uuid):
    """Unlink an asset from a customer."""
    from assets.models import Asset

    customer = _customer_branch_qs(request).filter(external_uuid=external_uuid).first()
    if not customer:
        return JsonResponse({'success': False, 'error': 'Customer not found.'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    asset_id = data.get('asset_id')
    asset_qs = Asset.objects.filter(pk=asset_id, company=request.company, customer_reference=customer)
    if not _is_admin(request.user):
        branch_ids = _get_user_branch_ids(request)
        asset_qs = asset_qs.filter(branch_id__in=branch_ids)

    asset = asset_qs.first()
    if not asset:
        return JsonResponse({'success': False, 'error': 'Asset not found or not linked to this customer.'}, status=404)

    asset.customer_reference = None
    asset.save(update_fields=['customer_reference', 'updated_at'])

    log_audit(
        request.user,
        'customer_asset_unlinked',
        asset=asset,
        details=f'Asset unlinked from customer {customer.full_name}',
        company=request.company,
        metadata={'customer_id': customer.pk, 'asset_id': asset.pk},
    )

    return JsonResponse({'success': True})


# ---------------------------------------------------------------------------
# Customer-to-Customer Asset Transfer API
# ---------------------------------------------------------------------------

@require_transfer_permission
@require_POST
def api_transfer_asset_between_customers(request, external_uuid):
    """
    Transfer an asset from the current customer to another customer.
    Creates an AssetTransfer record and updates customer_reference.
    """
    from assets.models import Asset, AssetTransfer

    source_customer = _customer_branch_qs(request).filter(external_uuid=external_uuid).first()
    if not source_customer:
        return JsonResponse({'success': False, 'error': 'Source customer not found.'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    asset_id = data.get('asset_id')
    target_uuid = data.get('target_customer_uuid')
    reason = (data.get('reason') or '').strip()

    if not asset_id or not target_uuid:
        return JsonResponse({'success': False, 'error': 'asset_id and target_customer_uuid are required.'}, status=400)

    target_customer = _customer_branch_qs(request).filter(external_uuid=target_uuid).first()
    if not target_customer:
        return JsonResponse({'success': False, 'error': 'Target customer not found.'}, status=404)

    if str(source_customer.external_uuid) == str(target_uuid):
        return JsonResponse({'success': False, 'error': 'Source and target customer must differ.'}, status=400)

    asset_qs = Asset.objects.filter(pk=asset_id, company=request.company, customer_reference=source_customer)
    if not _is_admin(request.user):
        branch_ids = _get_user_branch_ids(request)
        asset_qs = asset_qs.filter(branch_id__in=branch_ids)

    asset = asset_qs.first()
    if not asset:
        return JsonResponse({'success': False, 'error': 'Asset not found or not linked to source customer.'}, status=404)

    # Create AssetTransfer record for audit trail
    transfer = AssetTransfer.objects.create(
        company=request.company,
        asset=asset,
        initiator=request.user,
        from_user=asset.assigned_to,
        to_user=request.user,
        from_branch=asset.branch,
        to_branch=asset.branch,
        state=AssetTransfer.TransferState.COMPLETED,
        reason=reason or f'Customer transfer: {source_customer.full_name} → {target_customer.full_name}',
        context={
            'transfer_type': 'customer_to_customer',
            'from_customer_id': source_customer.pk,
            'from_customer_name': source_customer.full_name,
            'to_customer_id': target_customer.pk,
            'to_customer_name': target_customer.full_name,
        },
    )

    asset.customer_reference = target_customer
    asset.save(update_fields=['customer_reference', 'updated_at'])

    log_audit(
        request.user,
        'customer_asset_transferred',
        asset=asset,
        details=(
            f'Asset transferred from customer {source_customer.full_name} '
            f'to {target_customer.full_name}'
        ),
        company=request.company,
        metadata={
            'customer_id': source_customer.pk,
            'target_customer_id': target_customer.pk,
            'asset_id': asset.pk,
            'transfer_id': transfer.pk,
        },
    )

    return JsonResponse({
        'success': True,
        'transfer_id': transfer.pk,
        'target_customer': target_customer.full_name,
    })


# ---------------------------------------------------------------------------
# Branch Assignment API (admin only)
# ---------------------------------------------------------------------------

@api_admin_required
@require_POST
def api_assign_customer_branch(request, external_uuid):
    """Assign or reassign a customer to a branch (admin only)."""
    from tenancy.models import Branch

    customer = ExternalCustomerReference.objects.filter(
        company=request.company, external_uuid=external_uuid
    ).first()
    if not customer:
        return JsonResponse({'success': False, 'error': 'Customer not found.'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    branch_id = data.get('branch_id')
    if branch_id:
        branch = Branch.objects.filter(pk=branch_id, company=request.company, is_active=True).first()
        if not branch:
            return JsonResponse({'success': False, 'error': 'Branch not found.'}, status=404)
        customer.branch = branch
        branch_name = branch.name
    else:
        customer.branch = None
        branch_name = 'Unassigned'

    customer.save(update_fields=['branch', 'updated_at'])

    log_audit(
        request.user,
        'customer_branch_assigned',
        details=f'Customer {customer.full_name} assigned to branch: {branch_name}',
        company=request.company,
        metadata={'customer_id': customer.pk, 'branch_id': branch_id},
    )

    return JsonResponse({'success': True, 'branch': branch_name})


# ---------------------------------------------------------------------------
# Integration Settings Page (admin only)
# ---------------------------------------------------------------------------

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def integration_settings(request):
    """Dedicated integration settings page for admins."""
    if not _is_admin(request.user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied('Admin access required.')
    return render(request, 'integrations/integration_settings.html')


# ---------------------------------------------------------------------------
# Sync config & run (admin only — unchanged)
# ---------------------------------------------------------------------------

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
