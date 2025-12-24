from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from assets.models import Asset
from tenancy.mixins import company_required
from tenancy.models import Branch

from .models import Report
from .services import (
    ReportFilters,
    build_csv_bytes,
    build_excel_bytes,
    build_pdf_bytes,
    fetch_assets_cached,
    render_assets_dataframe,
)
import pandas as pd
from weasyprint import HTML

def is_admin_or_manager(user):
    return user.is_authenticated and user.role in ('admin', 'manager')

# Create your views here.

@login_required
@company_required
def reports_dashboard(request):
    """
    World-class reports dashboard with statistics, filtering, and analytics.
    Matches main dashboard quality standards.
    """
    from django.utils import timezone
    from datetime import timedelta
    from tenancy.policy_service import PolicyService
    
    # Multi-tenancy: Scope to company
    company = request.company
    user = request.user
    
    # Get available branches based on role and policy
    if user.role == 'admin':
        available_branches = Branch.objects.filter(
            company=company, 
            is_active=True
        ).order_by('name')
    else:
        # Managers and users see only assigned branches
        accessible_branch_ids = PolicyService.get_accessible_branches(user, company)
        available_branches = Branch.objects.filter(
            id__in=accessible_branch_ids,
            company=company
        ).order_by('name')
    
    # Base queryset with optimized queries
    # Report model has 'created_by' not 'generated_by'
    reports = Report.objects.filter(company=company).select_related(
        'created_by', 'branch'
    ).order_by('-created_at')
    
    # Branch filtering based on role
    if user.role != 'admin':
        # Managers and users see only reports from their branches
        user_branch_ids = available_branches.values_list('id', flat=True)
        reports = reports.filter(branch_id__in=user_branch_ids)
    
    # Apply filters
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    branch_filter = request.GET.get('branch')
    
    if status == 'generated':
        reports = reports.exclude(file="")
    elif status == 'pending':
        reports = reports.filter(file="")
    
    if date_from:
        reports = reports.filter(created_at__gte=date_from)
    if date_to:
        reports = reports.filter(created_at__lte=date_to + ' 23:59:59')
    if branch_filter:
        reports = reports.filter(branch_id=branch_filter)
    
    # Calculate statistics
    now = timezone.now()
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (first_day_of_month - timedelta(days=1)).replace(day=1)
    
    # Current month stats
    this_month_count = reports.filter(created_at__gte=first_day_of_month).count()
    last_month_count = reports.filter(
        created_at__gte=last_month_start,
        created_at__lt=first_day_of_month
    ).count()
    
    # Calculate trend percentage
    if last_month_count > 0:
        trend_percentage = round(((this_month_count - last_month_count) / last_month_count) * 100)
    else:
        trend_percentage = 100 if this_month_count > 0 else 0
    
    stats = {
        'total_reports': reports.count(),
        'this_month': this_month_count,
        'last_month': last_month_count,
        'trend_percentage': trend_percentage,
        'generated': reports.exclude(file="").count(),
        'pending': reports.filter(file="").count(),
    }
    
    context = {
        'reports': reports,
        'stats': stats,
        'available_branches': available_branches,
        'active_branch': getattr(request, 'branch', None),
        'asset_status_choices': Asset.STATUS_CHOICES,
        'request': request,
    }
    
    return render(request, 'reports/reports_dashboard_worldclass.html', context)

@login_required
@company_required
@user_passes_test(is_admin_or_manager, login_url='users:login')
@require_http_methods(["POST"])
def generate_report(request):
    """
    World-class report generation supporting multiple report types.
    Generates Excel, CSV, or PDF reports based on user selection.
    """
    report_type = request.POST.get('report_type', 'asset_summary')
    fmt = request.POST.get('format', 'excel').lower()

    # Validate report type
    valid_report_types = ['asset_summary', 'maintenance', 'custom']
    if report_type not in valid_report_types:
        messages.error(request, f'Invalid report type: {report_type}')
        return redirect(reverse('reports:reports_dashboard'))

    # Validate format
    if fmt not in ['excel', 'csv', 'pdf']:
        messages.error(request, 'Invalid format. Please choose Excel, CSV, or PDF.')
        return redirect(reverse('reports:reports_dashboard'))

    filters = ReportFilters(
        status=request.POST.get('status') or None,
        branch_id=request.POST.get('branch_id') or None,
        date_from=request.POST.get('date_from') or None,
        date_to=request.POST.get('date_to') or None,
    )

    branch = None
    if filters.branch_id:
        branch = Branch.objects.filter(pk=filters.branch_id, company=request.company).first()
        if branch is None:
            messages.error(request, 'Invalid branch selection for your company.')
            return redirect(reverse('reports:reports_dashboard'))

    # Generate report based on type
    try:
        if report_type == 'asset_summary':
            file_bytes, filename, content_type = _generate_asset_summary_report(
                request.company, branch, filters, fmt, request
            )
        elif report_type == 'maintenance':
            file_bytes, filename, content_type = _generate_maintenance_report(
                request.company, branch, filters, fmt, request
            )
        elif report_type == 'custom':
            file_bytes, filename, content_type = _generate_custom_report(
                request.company, branch, filters, fmt, request
            )
        else:
            messages.error(request, 'Report type not implemented yet.')
            return redirect(reverse('reports:reports_dashboard'))

        # Save report to database
        report = Report.objects.create(
            company=request.company,
            branch=branch,
            report_type=report_type,
            created_by=request.user,
            metadata={
                'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
                'generated_by': request.user.get_full_name() or request.user.username,
                'company': request.company.name,
                'branch': branch.name if branch else 'All Branches',
                'filters': filters.__dict__,
                'format': fmt,
            },
        )
        
        # Save file
        extension = filename.split('.')[-1]
        report.file.save(f'{report_type}_{report.pk}.{extension}', ContentFile(file_bytes))

        # Return file download
        response = HttpResponse(file_bytes, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        messages.success(request, f'{report_type.replace("_", " ").title()} report generated successfully!')
        return response

    except Exception as e:
        messages.error(request, f'Error generating report: {str(e)}')
        return redirect(reverse('reports:reports_dashboard'))


def _generate_asset_summary_report(company, branch, filters, fmt, request):
    """Generate comprehensive asset summary report."""
    assets = fetch_assets_cached(company, branch, filters)
    if not assets:
        raise ValueError('No assets found for the selected filters.')

    df = render_assets_dataframe(assets)
    metadata = {
        'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
        'generated_by': request.user.get_full_name() or request.user.username,
        'company': company.name,
        'branch': branch.name if branch else 'All Branches',
        'filters': filters.__dict__,
        'base_url': request.build_absolute_uri('/').rstrip('/'),
    }

    if fmt == 'excel':
        file_bytes = build_excel_bytes(df)
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        extension = 'xlsx'
    elif fmt == 'csv':
        file_bytes = build_csv_bytes(df)
        content_type = 'text/csv'
        extension = 'csv'
    elif fmt == 'pdf':
        file_bytes = build_pdf_bytes(assets, metadata)
        content_type = 'application/pdf'
        extension = 'pdf'

    filename = f"asset_summary_{timezone.now():%Y%m%d_%H%M%S}.{extension}"
    return file_bytes, filename, content_type


def _generate_maintenance_report(company, branch, filters, fmt, request):
    """Generate maintenance report with asset maintenance history."""
    from assets.models import MaintenanceRecord
    
    # Get assets with maintenance records
    assets_qs = Asset.objects.filter(company=company)
    if branch:
        assets_qs = assets_qs.filter(branch=branch)
    if filters.status:
        assets_qs = assets_qs.filter(status=filters.status)
    
    # Get maintenance records
    maintenance_qs = MaintenanceRecord.objects.filter(
        company=company
    ).select_related('asset', 'asset__category', 'performed_by')
    
    if branch:
        maintenance_qs = maintenance_qs.filter(branch=branch)
    if filters.date_from:
        maintenance_qs = maintenance_qs.filter(scheduled_date__gte=filters.date_from)
    if filters.date_to:
        maintenance_qs = maintenance_qs.filter(scheduled_date__lte=filters.date_to)
    
    maintenance_records = list(maintenance_qs.order_by('-scheduled_date'))
    
    if not maintenance_records:
        raise ValueError('No maintenance records found for the selected filters.')
    
    # Build DataFrame
    rows = []
    for record in maintenance_records:
        rows.append({
            'Asset': f"{record.asset.category.name} - {record.asset.asset_tag}",
            'Status': record.get_status_display(),
            'Scheduled Date': record.scheduled_date.strftime('%Y-%m-%d'),
            'Started': record.started_at.strftime('%Y-%m-%d %H:%M') if record.started_at else '—',
            'Completed': record.completed_at.strftime('%Y-%m-%d %H:%M') if record.completed_at else '—',
            'Performed By': record.performed_by.get_full_name() if record.performed_by else '—',
            'Cost': f"${record.cost:,.2f}" if record.cost else '—',
            'Description': record.description or '—',
        })
    
    df = pd.DataFrame(rows)
    
    if fmt == 'excel':
        file_bytes = build_excel_bytes(df)
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        extension = 'xlsx'
    elif fmt == 'csv':
        file_bytes = build_csv_bytes(df)
        content_type = 'text/csv'
        extension = 'csv'
    elif fmt == 'pdf':
        # Simple PDF generation for maintenance
        metadata = {
            'title': 'Maintenance Report',
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'generated_by': request.user.get_full_name() or request.user.username,
            'company': company.name,
            'branch': branch.name if branch else 'All Branches',
        }
        html_string = f"""
        <html>
        <head><style>
            body {{ font-family: Arial, sans-serif; }}
            h1 {{ color: #176B87; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #176B87; color: white; }}
        </style></head>
        <body>
            <h1>Maintenance Report</h1>
            <p><strong>Company:</strong> {metadata['company']}</p>
            <p><strong>Branch:</strong> {metadata['branch']}</p>
            <p><strong>Generated:</strong> {metadata['generated_at']} by {metadata['generated_by']}</p>
            {df.to_html(index=False, escape=False)}
        </body>
        </html>
        """
        file_bytes = HTML(string=html_string).write_pdf()
        content_type = 'application/pdf'
        extension = 'pdf'
    
    filename = f"maintenance_report_{timezone.now():%Y%m%d_%H%M%S}.{extension}"
    return file_bytes, filename, content_type


def _generate_custom_report(company, branch, filters, fmt, request):
    """Generate custom report with user-selected fields."""
    # For now, generate a comprehensive report with all available data
    assets = fetch_assets_cached(company, branch, filters)
    if not assets:
        raise ValueError('No assets found for the selected filters.')
    
    # Build comprehensive DataFrame with additional fields
    rows = []
    for asset in assets:
        row = {
            'ID': asset.pk,
            'UUID': str(asset.uuid),
            'Category': asset.category.name,
            'Asset Tag': asset.asset_tag,
            'Serial Number': asset.serial_number or '—',
            'Status': asset.get_status_display(),
            'Branch': asset.branch.name if asset.branch else 'Head Office',
            'Assigned To': str(asset.assigned_to) if asset.assigned_to else 'Unassigned',
            'Purchase Date': asset.purchase_date.strftime('%Y-%m-%d') if asset.purchase_date else '—',
            'Purchase Price': f"${asset.purchase_price:,.2f}" if asset.purchase_price else '—',
            'Current Value': f"${asset.current_value:,.2f}" if asset.current_value else '—',
            'Warranty Expiry': asset.warranty_expiry.strftime('%Y-%m-%d') if asset.warranty_expiry else '—',
            'Created': asset.created_at.strftime('%Y-%m-%d %H:%M'),
            'Updated': asset.updated_at.strftime('%Y-%m-%d %H:%M'),
        }
        
        # Add dynamic fields
        for key, value in (asset.dynamic_data or {}).items():
            normalized_key = key.replace("_", " ").title()
            row[normalized_key] = value if isinstance(value, (int, float)) else str(value)
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    if fmt == 'excel':
        file_bytes = build_excel_bytes(df)
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        extension = 'xlsx'
    elif fmt == 'csv':
        file_bytes = build_csv_bytes(df)
        content_type = 'text/csv'
        extension = 'csv'
    elif fmt == 'pdf':
        metadata = {
            'title': 'Custom Report',
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'generated_by': request.user.get_full_name() or request.user.username,
            'company': company.name,
            'branch': branch.name if branch else 'All Branches',
        }
        html_string = f"""
        <html>
        <head><style>
            body {{ font-family: Arial, sans-serif; }}
            h1 {{ color: #176B87; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
            th {{ background-color: #176B87; color: white; }}
        </style></head>
        <body>
            <h1>Custom Report</h1>
            <p><strong>Company:</strong> {metadata['company']}</p>
            <p><strong>Branch:</strong> {metadata['branch']}</p>
            <p><strong>Generated:</strong> {metadata['generated_at']} by {metadata['generated_by']}</p>
            {df.to_html(index=False, escape=False)}
        </body>
        </html>
        """
        file_bytes = HTML(string=html_string).write_pdf()
        content_type = 'application/pdf'
        extension = 'pdf'
    
    filename = f"custom_report_{timezone.now():%Y%m%d_%H%M%S}.{extension}"
    return file_bytes, filename, content_type


@login_required
@company_required
@require_http_methods(["GET"])
def api_report_trend(request):
    """Return report generation counts over time for the trend chart.

    Period is controlled via the ``period`` query parameter: ``7d``, ``30d``, or ``90d``.
    Data is scoped to the current company and, for non-admins, to branches the user
    is allowed to access via the tenancy policy service.
    """
    from datetime import timedelta
    from django.db.models import Count
    from tenancy.policy_service import PolicyService

    company = request.company
    user = request.user

    period = request.GET.get('period', '30d')
    days_map = {
        '7d': 7,
        '30d': 30,
        '90d': 90,
    }
    days = days_map.get(period, 30)

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)

    qs = Report.objects.filter(
        company=company,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )

    # Branch-level scoping for managers/users
    if getattr(user, 'role', None) != 'admin':
        accessible_branch_ids = PolicyService.get_accessible_branches(user, company)
        qs = qs.filter(branch_id__in=list(accessible_branch_ids))

    # Aggregate counts per day
    aggregate = qs.values('created_at__date').annotate(count=Count('id'))
    counts_by_date = {row['created_at__date']: row['count'] for row in aggregate}

    labels = []
    data = []
    for offset in range(days):
        current_date = start_date + timedelta(days=offset)
        labels.append(current_date.strftime('%b %d'))
        data.append(counts_by_date.get(current_date, 0))

    return JsonResponse({
        'labels': labels,
        'data': data,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    })


@login_required
@company_required
@require_http_methods(["GET"])
def api_report_types(request):
    """Return distribution of report categories for the types chart.

    Only supported dashboard categories are returned (asset_summary, maintenance, custom).
    Results are scoped to the current company and, for non-admins, to accessible branches.
    """
    from django.db.models import Count
    from tenancy.policy_service import PolicyService

    company = request.company
    user = request.user

    qs = Report.objects.filter(company=company)

    # Branch-level scoping for managers/users
    if getattr(user, 'role', None) != 'admin':
        accessible_branch_ids = PolicyService.get_accessible_branches(user, company)
        qs = qs.filter(branch_id__in=list(accessible_branch_ids))

    # Normalized labels for the dashboard
    type_labels = {
        'asset_summary': 'Asset Summary',
        'maintenance': 'Maintenance',
        'custom': 'Custom',
    }
    counts = {key: 0 for key in type_labels.keys()}

    for row in qs.values('report_type').annotate(count=Count('id')):
        rtype = row['report_type']
        if rtype in counts:
            counts[rtype] = row['count']

    labels = [label for _key, label in type_labels.items()]
    data = [counts[key] for key in type_labels.keys()]

    return JsonResponse({
        'labels': labels,
        'data': data,
        'total': sum(data),
    })
