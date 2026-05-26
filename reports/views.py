from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from assets.models import Asset
from audit.utils import BULK_EXPORT_ACTION, log_audit
from tenancy.mixins import company_required
from tenancy.models import Branch

from .models import Report
from .services import (
    ReportFilters,
    build_individual_excel_bytes,
    build_individual_pdf_bytes,
    build_csv_bytes,
    build_excel_bytes,
    build_pdf_bytes,
    fetch_individual_report_data,
    fetch_assets_cached,
    attach_report_branch_labels,
    get_available_individual_report_users,
    render_individual_assets_dataframe,
    render_assets_dataframe,
    user_can_access_report_branch,
    validate_report_filters,
)
import pandas as pd


def _get_weasyprint_html():
    from weasyprint import HTML

    return HTML

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
    
    available_report_users = attach_report_branch_labels(
        get_available_individual_report_users(company, user),
        company,
    )

    context = {
        'reports': reports,
        'stats': stats,
        'available_branches': available_branches,
        'available_report_users': available_report_users,
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

    rtype_db = fmt

    # Validate report type
    valid_report_types = ['asset_summary', 'maintenance', 'custom', 'individual']
    if report_type not in valid_report_types:
        messages.error(request, f'Invalid report type: {report_type}')
        return redirect(reverse('reports:reports_dashboard'))

    # Validate format
    if fmt not in ['excel', 'csv', 'pdf']:
        messages.error(request, 'Invalid format. Please choose Excel, CSV, or PDF.')
        return redirect(reverse('reports:reports_dashboard'))

    subject_user = None
    filters = ReportFilters(
        status=request.POST.get('status') or None,
        branch_id=request.POST.get('branch_id') or None,
        date_from=request.POST.get('date_from') or None,
        date_to=request.POST.get('date_to') or None,
        user_id=request.POST.get('user_id') or None,
    )
    filter_error = validate_report_filters(filters)
    if filter_error:
        messages.error(request, filter_error)
        return redirect(reverse('reports:reports_dashboard'))

    branch = None
    if filters.branch_id:
        branch = Branch.objects.filter(pk=filters.branch_id, company=request.company).first()
        if branch is None:
            messages.error(request, 'Invalid branch selection for your company.')
            return redirect(reverse('reports:reports_dashboard'))
        if not user_can_access_report_branch(request.company, request.user, branch):
            messages.error(request, 'You do not have access to the selected branch.')
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
        elif report_type == 'individual':
            file_bytes, filename, content_type, subject_user = _generate_individual_report(
                request.company, branch, filters, fmt, request
            )
        else:
            messages.error(request, 'Report type not implemented yet.')
            return redirect(reverse('reports:reports_dashboard'))

        report = Report.objects.create(
            company=request.company,
            branch=branch,
            report_type=rtype_db,
            created_by=request.user,
            metadata={
                'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
                'generated_by': request.user.get_full_name() or request.user.username,
                'company': request.company.name,
                'branch': branch.name if branch else 'All Branches',
                'filters': filters.__dict__,
                'format': fmt,
                'report_type': report_type,
                'subject_user_id': getattr(subject_user, 'pk', None),
                'subject_user_name': (
                    (subject_user.get_full_name() or subject_user.username)
                    if subject_user
                    else ''
                ),
            },
        )
        
        extension = filename.split('.')[-1]
        report.file.save(f'{report_type}_{report.pk}.{extension}', ContentFile(file_bytes))

        log_audit(
            request.user,
            BULK_EXPORT_ACTION,
            None,
            f'Generated {report_type.replace("_", " ")} report in {fmt} format.',
            company=request.company,
            branch=branch,
            related_user=subject_user,
            metadata={
                'report_id': report.pk,
                'report_type': report_type,
                'format': fmt,
                'subject_user_id': getattr(subject_user, 'pk', None),
            },
        )

        response = HttpResponse(file_bytes, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        messages.success(request, f'{report_type.replace("_", " ").title()} report generated successfully!')
        return response

    except Exception as e:
        messages.error(request, f'Error generating report: {str(e)}')
        return redirect(reverse('reports:reports_dashboard'))


@login_required
@company_required
@user_passes_test(is_admin_or_manager, login_url='users:login')
@require_http_methods(["GET"])
def export_individual_report(request, user_id):
    """Direct staff-detail export for one person's report."""
    fmt = request.GET.get('format', 'pdf').lower()
    if fmt not in ['excel', 'csv', 'pdf']:
        messages.error(request, 'Invalid format. Please choose Excel, CSV, or PDF.')
        return redirect(reverse('settings:staff_detail', kwargs={'user_id': user_id}))

    branch = None
    branch_id = request.GET.get('branch_id') or None
    if branch_id:
        branch = Branch.objects.filter(pk=branch_id, company=request.company).first()
        if branch is None or not user_can_access_report_branch(request.company, request.user, branch):
            messages.error(request, 'Invalid branch selection for your company.')
            return redirect(reverse('settings:staff_detail', kwargs={'user_id': user_id}))

    filters = ReportFilters(
        status=request.GET.get('status') or None,
        branch_id=branch_id,
        date_from=request.GET.get('date_from') or None,
        date_to=request.GET.get('date_to') or None,
        user_id=user_id,
    )
    filter_error = validate_report_filters(filters)
    if filter_error:
        messages.error(request, filter_error)
        return redirect(reverse('settings:staff_detail', kwargs={'user_id': user_id}))

    try:
        file_bytes, filename, content_type, subject_user = _generate_individual_report(
            request.company, branch, filters, fmt, request
        )

        report = Report.objects.create(
            company=request.company,
            branch=branch,
            report_type=fmt,
            created_by=request.user,
            metadata={
                'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
                'generated_by': request.user.get_full_name() or request.user.username,
                'company': request.company.name,
                'branch': branch.name if branch else 'All Branches',
                'filters': filters.__dict__,
                'format': fmt,
                'report_type': 'individual',
                'subject_user_id': subject_user.pk,
                'subject_user_name': subject_user.get_full_name() or subject_user.username,
                'source': 'staff_detail',
            },
        )
        extension = filename.split('.')[-1]
        report.file.save(f'individual_{report.pk}.{extension}', ContentFile(file_bytes))

        log_audit(
            request.user,
            BULK_EXPORT_ACTION,
            None,
            f'Generated individual report for {subject_user.get_full_name() or subject_user.username} from staff detail.',
            company=request.company,
            branch=branch,
            related_user=subject_user,
            metadata={
                'report_id': report.pk,
                'report_type': 'individual',
                'format': fmt,
                'subject_user_id': subject_user.pk,
                'source': 'staff_detail',
            },
        )

        response = HttpResponse(file_bytes, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f'Error generating individual report: {str(e)}')
        return redirect(reverse('settings:staff_detail', kwargs={'user_id': user_id}))


def _generate_asset_summary_report(company, branch, filters, fmt, request):
    """Generate comprehensive asset summary report."""
    assets = fetch_assets_cached(company, branch, filters)

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
        maintenance_qs = maintenance_qs.filter(scheduled_for__gte=filters.date_from)
    if filters.date_to:
        maintenance_qs = maintenance_qs.filter(scheduled_for__lte=filters.date_to)
    
    maintenance_records = list(maintenance_qs.order_by('-scheduled_for'))
    
    # Build DataFrame
    rows = []
    for record in maintenance_records:
        rows.append({
            'Asset': f"{record.asset.category.name} - {record.asset.asset_tag}",
            'Status': record.get_status_display(),
            'Scheduled Date': record.scheduled_for.strftime('%Y-%m-%d'),
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
        file_bytes = _get_weasyprint_html()(string=html_string).write_pdf()
        content_type = 'application/pdf'
        extension = 'pdf'
    
    filename = f"maintenance_report_{timezone.now():%Y%m%d_%H%M%S}.{extension}"
    return file_bytes, filename, content_type


def _generate_custom_report(company, branch, filters, fmt, request):
    """Generate custom report with user-selected fields."""
    # For now, generate a comprehensive report with all available data
    assets = fetch_assets_cached(company, branch, filters)
    
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
        file_bytes = _get_weasyprint_html()(string=html_string).write_pdf()
        content_type = 'application/pdf'
        extension = 'pdf'
    
    filename = f"custom_report_{timezone.now():%Y%m%d_%H%M%S}.{extension}"
    return file_bytes, filename, content_type


def _generate_individual_report(company, branch, filters, fmt, request):
    """Generate a detailed report for one person within the current tenant."""
    if not filters.user_id:
        raise ValueError('Please select a person for the individual report.')

    subject_user = get_available_individual_report_users(company, request.user).filter(pk=filters.user_id).first()
    if subject_user is None:
        raise ValueError('Invalid person selection for your company or branch access.')
    subject_user = attach_report_branch_labels([subject_user], company)[0]

    report_data = fetch_individual_report_data(company, subject_user, filters, branch)
    metadata = {
        'title': 'Individual Report',
        'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
        'generated_by': request.user.get_full_name() or request.user.username,
        'company': company.name,
        'company_logo': request.build_absolute_uri(company.logo.url) if getattr(company, 'logo', None) else '',
        'branch': branch.name if branch else 'All Branches',
        'filters': filters.__dict__,
        'base_url': request.build_absolute_uri('/').rstrip('/'),
        'subject_user': subject_user.get_full_name() or subject_user.username,
        'subject_branch': subject_user.report_branch_label,
        'report_reference': f"IND-{timezone.now():%Y%m%d%H%M}-{subject_user.pk}",
    }

    if fmt == 'excel':
        file_bytes = build_individual_excel_bytes(report_data)
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        extension = 'xlsx'
    elif fmt == 'csv':
        df = render_individual_assets_dataframe(report_data)
        file_bytes = build_csv_bytes(df)
        content_type = 'text/csv'
        extension = 'csv'
    elif fmt == 'pdf':
        file_bytes = build_individual_pdf_bytes(report_data, metadata)
        content_type = 'application/pdf'
        extension = 'pdf'

    filename = f"individual_report_{subject_user.username}_{timezone.now():%Y%m%d_%H%M%S}.{extension}"
    return file_bytes, filename, content_type, subject_user


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

    Only supported dashboard categories are returned.
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
        'individual': 'Individual',
    }
    counts = {key: 0 for key in type_labels.keys()}

    # Count by canonical report type stored in metadata.report_type (fallbacks for legacy rows)
    for report in qs.only('metadata', 'report_type'):
        meta = report.metadata or {}
        canonical = str(meta.get('report_type') or '').strip().lower()
        if not canonical:
            # Legacy fallback: some rows stored canonical token in report_type
            rt = (report.report_type or '').lower()
            if rt in {'asset_summary', 'maintenance', 'custom', 'individual'}:
                canonical = rt
        if canonical in counts:
            counts[canonical] += 1

    labels = [label for _key, label in type_labels.items()]
    data = [counts[key] for key in type_labels.keys()]

    return JsonResponse({
        'labels': labels,
        'data': data,
        'total': sum(data),
    })
