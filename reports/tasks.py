"""
Celery Tasks for Report Generation

Async report generation for:
- PDF reports (WeasyPrint)
- Excel exports (openpyxl)
- Weekly summaries
- Scheduled reports

Following best practices from ServiceNow ITAM, IBM Maximo, SAP EAM
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import Report
from .services import (
    build_pdf_bytes,
    build_excel_bytes,
    fetch_assets_cached,
    ReportFilters,
)
from tenancy.models import Alert, Company
from users.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, time_limit=300)
def generate_asset_report_async(self, report_id, company_id):
    """
    Generate asset report asynchronously (PDF)
    
    Args:
        report_id: Report ID
        company_id: Company ID for multi-tenancy
        
    Returns:
        bool: True if generated successfully
    """
    try:
        # Get report with company validation
        report = Report.objects.select_related('company', 'created_by').get(
            id=report_id, company_id=company_id
        )
        
        # Update status
        report.status = 'generating'
        report.save(update_fields=['status'])
        
        # Build filters from report metadata
        filters = ReportFilters(
            company_id=company_id,
            branch_id=report.branch_id,
            status=report.metadata.get('status'),
            category_id=report.metadata.get('category_id'),
            search=report.metadata.get('search'),
        )
        
        # Fetch assets
        assets = fetch_assets_cached(filters)
        
        # Generate PDF
        pdf_bytes = build_pdf_bytes(
            assets=assets,
            company=report.company,
            branch=report.branch,
            generated_by=report.created_by,
        )
        
        # Save PDF to report
        filename = f"asset_report_{report.company.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        report.file.save(filename, ContentFile(pdf_bytes), save=False)
        report.status = 'completed'
        report.save(update_fields=['file', 'status'])
        
        # Notify user
        Alert.objects.create(
            company_id=company_id,
            user=report.created_by,
            level=Alert.LEVEL_SUCCESS,
            title="Report Generated",
            message=f"Your asset report is ready for download",
            context={'report_id': report.id}
        )
        
        logger.info(f"Report {report_id} generated successfully")
        return True
        
    except Report.DoesNotExist:
        logger.error(f"Report {report_id} not found for company {company_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error generating report {report_id}: {e}", exc_info=True)
        
        # Update report status
        try:
            report = Report.objects.get(id=report_id)
            report.status = 'failed'
            report.save(update_fields=['status'])
        except:
            pass
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)


@shared_task(bind=True, max_retries=2, time_limit=300)
def generate_excel_report_async(self, report_id, company_id):
    """
    Generate Excel report asynchronously
    
    Args:
        report_id: Report ID
        company_id: Company ID for multi-tenancy
        
    Returns:
        bool: True if generated successfully
    """
    try:
        # Get report with company validation
        report = Report.objects.select_related('company', 'created_by').get(
            id=report_id, company_id=company_id
        )
        
        # Update status
        report.status = 'generating'
        report.save(update_fields=['status'])
        
        # Build filters
        filters = ReportFilters(
            company_id=company_id,
            branch_id=report.branch_id,
            status=report.metadata.get('status'),
            category_id=report.metadata.get('category_id'),
            search=report.metadata.get('search'),
        )
        
        # Fetch assets
        assets = fetch_assets_cached(filters)
        
        # Generate Excel
        excel_bytes = build_excel_bytes(
            assets=assets,
            company=report.company,
            branch=report.branch,
        )
        
        # Save Excel to report
        filename = f"asset_report_{report.company.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        report.file.save(filename, ContentFile(excel_bytes), save=False)
        report.status = 'completed'
        report.save(update_fields=['file', 'status'])
        
        # Notify user
        Alert.objects.create(
            company_id=company_id,
            user=report.created_by,
            level=Alert.LEVEL_SUCCESS,
            title="Excel Report Generated",
            message=f"Your Excel report is ready for download",
            context={'report_id': report.id}
        )
        
        logger.info(f"Excel report {report_id} generated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error generating Excel report {report_id}: {e}", exc_info=True)
        
        # Update report status
        try:
            report = Report.objects.get(id=report_id)
            report.status = 'failed'
            report.save(update_fields=['status'])
        except:
            pass
        
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)


@shared_task(bind=True)
def generate_weekly_summary_reports(self):
    """
    Generate weekly summary reports for all companies
    Runs every Monday at 7 AM
    """
    try:
        companies = Company.objects.all()
        
        for company in companies:
            # Get admins for this company
            admins = User.objects.filter(company=company, role='admin')
            
            for admin in admins:
                # Create report
                report = Report.objects.create(
                    company=company,
                    created_by=admin,
                    report_type='weekly_summary',
                    status='pending',
                    metadata={
                        'start_date': (timezone.now() - timedelta(days=7)).isoformat(),
                        'end_date': timezone.now().isoformat(),
                    }
                )
                
                # Generate report async
                generate_asset_report_async.delay(report.id, company.id)
        
        logger.info(f"Scheduled weekly summary reports for {companies.count()} companies")
        
    except Exception as e:
        logger.error(f"Error generating weekly summary reports: {e}", exc_info=True)
