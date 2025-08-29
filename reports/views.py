from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Report
from django.http import HttpResponse
import pandas as pd
from assets.models import Asset
from django.core.files.base import ContentFile
from django.urls import reverse
import io

def is_admin_or_manager(user):
    return user.is_authenticated and user.role in ('admin', 'manager')

# Create your views here.

@login_required
def reports_dashboard(request):
    reports = Report.objects.all().order_by('-created_at')
    status = request.GET.get('status')
    if status == 'generated':
        reports = reports.exclude(file="")
    elif status == 'queued':
        reports = reports.filter(file="")
    return render(request, 'reports/reports_dashboard.html', {'reports': reports})

@login_required
@user_passes_test(is_admin_or_manager, login_url='users:login')
def generate_report(request):
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        fmt = request.POST.get('format')
        if report_type == 'asset_summary':
            # Gather asset data
            assets = Asset.objects.select_related('category', 'assigned_to').all()
            data = []
            for asset in assets:
                data.append({
                    'ID': asset.pk,
                    'Category': asset.category.name,
                    'Status': asset.status,
                    'Assigned To': str(asset.assigned_to) if asset.assigned_to else '',
                    'Created': asset.created_at.strftime('%Y-%m-%d %H:%M'),
                    'Updated': asset.updated_at.strftime('%Y-%m-%d %H:%M'),
                    **asset.dynamic_data
                })
            df = pd.DataFrame(data)
            # Generate file
            if fmt == 'excel':
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Assets')
                file_content = buffer.getvalue()
                ext = 'xlsx'
            elif fmt == 'csv':
                file_content = df.to_csv(index=False).encode('utf-8')
                ext = 'csv'
            else:
                return HttpResponse('Invalid format', status=400)
            # Save to Report model
            report = Report.objects.create(
                report_type=fmt,
                created_by=request.user
            )
            report.file.save(f'asset_summary_{report.pk}.{ext}', ContentFile(file_content))
            report.save()
            return redirect(reverse('reports_dashboard'))
    return HttpResponse('Invalid request', status=400)
