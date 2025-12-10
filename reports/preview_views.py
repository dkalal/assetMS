"""
WORLD-CLASS Export Preview API Views
=====================================

API endpoints for export preview functionality across all report types.

Features:
- Unified preview API for assets, reports, maintenance exports
- Real-time validation and error detection
- Multi-tenancy and security enforced
- Performance optimized with caching
- Audit logging for compliance

Author: AssetMS Development Team
Date: November 2025
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect

from tenancy.mixins import company_required
from tenancy.models import Branch
from audit.utils import log_audit
from users.utils import can

from .services import ReportFilters
from .preview_service import ExportPreviewService


@require_http_methods(["POST"])
@csrf_protect
@login_required
@company_required
def api_preview_export(request):
    """
    Unified API endpoint for export preview
    
    Supports all export types:
    - Asset exports (from asset list)
    - Report exports (asset_summary, maintenance, custom)
    - Any other exportable data
    
    Request Body (JSON):
        {
            "report_type": "asset_summary",
            "format": "xlsx",
            "status": "active",
            "branch_id": 123,
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "preview_limit": 50
        }
    
    Response (JSON):
        {
            "success": true,
            "preview_data": [...],
            "columns": [...],
            "column_metadata": [...],
            "metrics": {...},
            "filters_applied": {...},
            ...
        }
    
    Security:
    - Authentication required
    - Company-scoped (multi-tenancy)
    - Permission check (export_data)
    - Audit logged
    
    Performance:
    - Cached for 5 minutes
    - < 500ms response time
    - Limited to 100 preview rows
    """
    import json
    
    user = request.user
    company = request.company
    
    # Permission check
    if not can(user, 'export_data'):
        return JsonResponse({
            'success': False,
            'error': 'Insufficient permissions. You do not have export privileges.'
        }, status=403)
    
    # Parse request body
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body.'
        }, status=400)
    
    # Extract parameters
    report_type = data.get('report_type', 'asset_summary')
    export_format = data.get('format', 'xlsx').lower()
    preview_limit = int(data.get('preview_limit', 50))
    
    # Validate report type
    valid_report_types = ['asset_summary', 'maintenance', 'custom']
    if report_type not in valid_report_types:
        return JsonResponse({
            'success': False,
            'error': f'Invalid report type. Supported types: {", ".join(valid_report_types)}'
        }, status=400)
    
    # Validate format
    valid_formats = ['csv', 'excel', 'xlsx', 'pdf']
    if export_format not in valid_formats:
        return JsonResponse({
            'success': False,
            'error': f'Invalid format. Supported formats: {", ".join(valid_formats)}'
        }, status=400)
    
    # Build filters
    filters = ReportFilters(
        status=data.get('status') or None,
        branch_id=data.get('branch_id') or None,
        date_from=data.get('date_from') or None,
        date_to=data.get('date_to') or None,
    )
    
    # Get branch (if specified)
    branch = None
    if filters.branch_id:
        try:
            branch = Branch.objects.get(
                pk=filters.branch_id,
                company=company,
                is_active=True
            )
        except Branch.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid branch selection for your company.'
            }, status=400)
    
    # Generate preview
    try:
        service = ExportPreviewService()
        result = service.generate_preview(
            company=company,
            report_type=report_type,
            export_format=export_format,
            filters=filters,
            branch=branch,
            preview_limit=preview_limit,
            user=user
        )
        
        # Audit log
        log_audit(
            user,
            'export_preview',
            None,
            f'Export preview: {result.metrics.total_rows} rows, format: {export_format}, type: {report_type}',
            company=company,
            metadata={
                'report_type': report_type,
                'format': export_format,
                'total_rows': result.metrics.total_rows,
                'preview_rows': result.metrics.preview_rows,
                'filters': filters.__dict__,
                'branch': branch.name if branch else None,
            }
        )
        
        # Return preview result
        return JsonResponse(result.to_dict())
        
    except Exception as e:
        # Log error
        log_audit(
            user,
            'export_preview_error',
            None,
            f'Export preview failed: {str(e)}',
            company=company,
            metadata={
                'report_type': report_type,
                'format': export_format,
                'error': str(e),
            }
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Preview generation failed: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@csrf_protect
@login_required
@company_required
def api_preview_asset_export(request):
    """
    Preview asset export from asset list page
    
    This is a specialized endpoint for the asset list page that supports
    bulk export of selected assets with additional filters.
    
    Request Body (JSON):
        {
            "format": "xlsx",
            "category": "category_id",
            "status": "active",
            "search": "search_term",
            "selected_ids": "1,2,3",
            "branch": "branch_id"
        }
    
    Response: Same as api_preview_export
    """
    import json
    from assets.models import Asset, AssetCategory
    from django.db.models import Q
    
    user = request.user
    company = request.company
    
    # Permission check
    if not can(user, 'export_data'):
        return JsonResponse({
            'success': False,
            'error': 'Insufficient permissions.'
        }, status=403)
    
    # Parse request
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON.'
        }, status=400)
    
    export_format = data.get('format', 'xlsx').lower()
    selected_ids = data.get('selected_ids', '')
    preview_limit = int(data.get('preview_limit', 50))
    
    # Build asset queryset
    assets = Asset.objects.filter(
        company=company
    ).select_related('category', 'branch', 'assigned_to')
    
    # Apply filters
    if selected_ids:
        # Bulk export of selected assets
        id_list = [int(pk) for pk in str(selected_ids).split(',') if pk.strip().isdigit()]
        assets = assets.filter(pk__in=id_list)
    else:
        # Filter by parameters
        category = data.get('category')
        status = data.get('status')
        search = data.get('search')
        branch = data.get('branch')
        
        if category:
            assets = assets.filter(category__id=category)
        if status:
            assets = assets.filter(status=status)
        if branch:
            assets = assets.filter(branch__id=branch)
        if search:
            assets = assets.filter(
                Q(dynamic_data__name__icontains=search) |
                Q(dynamic_data__model__icontains=search) |
                Q(description__icontains=search)
            )
    
    # Get counts
    total_count = assets.count()
    preview_assets = list(assets[:preview_limit])
    
    # Serialize preview data
    preview_data = []
    for asset in preview_assets:
        row = {
            'id': asset.id,
            'uuid': str(asset.uuid),
            'category': asset.category.name if asset.category else '-',
            'branch': asset.branch.name if asset.branch else '-',
            'status': asset.get_status_display(),
            'assigned_to': asset.assigned_to.get_full_name() if asset.assigned_to else 'Unassigned',
            'created_at': asset.created_at.strftime('%Y-%m-%d %H:%M'),
        }
        
        # Add dynamic fields
        if asset.dynamic_data:
            for key, value in asset.dynamic_data.items():
                row[key] = value if value is not None else '-'
        
        preview_data.append(row)
    
    # Get columns
    columns = list(preview_data[0].keys()) if preview_data else []
    
    # Build filters summary
    filters_applied = {}
    if data.get('category'):
        try:
            cat = AssetCategory.objects.get(pk=data['category'], company=company)
            filters_applied['category'] = cat.name
        except AssetCategory.DoesNotExist:
            pass
    if data.get('status'):
        filters_applied['status'] = data['status']
    if data.get('search'):
        filters_applied['search'] = data['search']
    if data.get('branch'):
        try:
            br = Branch.objects.get(pk=data['branch'], company=company)
            filters_applied['branch'] = br.name
        except Branch.DoesNotExist:
            pass
    
    # Calculate metrics
    has_more = total_count > preview_limit
    size_estimate = {
        'csv': 0.5,
        'excel': 1.0,
        'xlsx': 1.0,
        'pdf': 2.0,
    }
    estimated_size_kb = int(total_count * size_estimate.get(export_format, 1.0))
    
    # Warnings
    warnings = []
    if total_count > 10000:
        warnings.append(f'Large export ({total_count:,} rows). Consider adding filters.')
    if estimated_size_kb > 50000:
        warnings.append(f'Estimated file size: ~{estimated_size_kb//1024} MB')
    
    # Audit log
    log_audit(
        user,
        'export_preview',
        None,
        f'Asset export preview: {total_count} assets, format: {export_format}',
        company=company,
        metadata={
            'total_count': total_count,
            'format': export_format,
            'filters': filters_applied
        }
    )
    
    # Return response
    return JsonResponse({
        'success': True,
        'preview_data': preview_data,
        'columns': columns,
        'total_count': total_count,
        'preview_count': min(preview_limit, total_count),
        'has_more': has_more,
        'format': export_format,
        'filters_applied': filters_applied,
        'estimated_file_size_kb': estimated_size_kb,
        'warnings': warnings,
        'company_name': company.name,
        'generated_at': user.username,
    })
