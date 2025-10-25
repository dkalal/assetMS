from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from django.http import HttpResponse
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

def is_admin_or_manager(user):
    return user.is_authenticated and user.role in ('admin', 'manager')

# Create your views here.

@login_required
@company_required
def reports_dashboard(request):
    reports = Report.objects.filter(company=request.company).order_by('-created_at')
    if request.branch:
        reports = reports.filter(branch=request.branch)

    status = request.GET.get('status')
    if status == 'generated':
        reports = reports.exclude(file="")

    context = {
        'reports': reports,
        'available_branches': getattr(request, 'available_branches', []),
        'active_branch': getattr(request, 'branch', None),
        'asset_status_choices': Asset.STATUS_CHOICES,
    }
    return render(request, 'reports/reports_dashboard.html', context)

@login_required
@company_required
@user_passes_test(is_admin_or_manager, login_url='users:login')
@require_http_methods(["POST"])
def generate_report(request):
    report_type = request.POST.get('report_type', 'asset_summary')
    fmt = request.POST.get('format', 'excel').lower()

    if report_type != 'asset_summary':
        return HttpResponse('Unsupported report type', status=400)

    filters = ReportFilters(
        status=request.POST.get('status') or None,
        branch_id=request.POST.get('branch_id') or None,
        date_from=request.POST.get('date_from') or None,
        date_to=request.POST.get('date_to') or None,
    )

    branch = request.branch
    if filters.branch_id:
        branch = Branch.objects.filter(pk=filters.branch_id, company=request.company).first()
        if branch is None:
            messages.error(request, 'Invalid branch selection for your company.')
            return redirect(reverse('reports_dashboard'))

    assets = fetch_assets_cached(request.company, branch, filters)
    if not assets:
        messages.warning(request, 'No assets found for the selected filters.')
        return redirect(reverse('reports_dashboard'))

    df = render_assets_dataframe(assets)
    metadata = {
        'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
        'generated_by': request.user.get_full_name() or request.user.username,
        'company': request.company.name if request.company else '',
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
    else:
        return HttpResponse('Invalid format', status=400)

    report = Report.objects.create(
        company=request.company,
        branch=branch,
        report_type=fmt,
        created_by=request.user,
        metadata=metadata,
    )
    report.file.save(f'asset_summary_{report.pk}.{extension}', ContentFile(file_bytes))

    filename = f"asset_summary_{timezone.now():%Y%m%d_%H%M%S}.{extension}"
    response = HttpResponse(file_bytes, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
