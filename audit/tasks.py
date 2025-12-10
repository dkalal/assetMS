"""
Celery Tasks for Audit Log Management

Async tasks for:
- Audit log archival
- Compliance reporting
- Data retention

Following best practices from ServiceNow ITAM, IBM Maximo, SAP EAM
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import AuditLog
from tenancy.models import Company

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def archive_old_audit_logs(self):
    """
    Archive audit logs older than 90 days
    Runs weekly on Sunday at 1 AM
    
    In production, this would:
    1. Export old logs to cold storage (S3, etc.)
    2. Compress and archive
    3. Delete from active database
    
    For now, we just log the count
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=90)
        
        companies = Company.objects.all()
        
        for company in companies:
            old_logs = AuditLog.objects.filter(
                company=company,
                timestamp__lt=cutoff_date
            )
            
            count = old_logs.count()
            
            if count > 0:
                logger.info(f"Company {company.name}: {count} audit logs eligible for archival")
                
                # In production, export to cold storage here
                # old_logs_data = list(old_logs.values())
                # export_to_s3(old_logs_data, company.id)
                
                # Then delete from active database
                # old_logs.delete()
        
        logger.info("Audit log archival task completed")
        
    except Exception as e:
        logger.error(f"Error archiving audit logs: {e}", exc_info=True)


@shared_task(bind=True)
def generate_compliance_report(self, company_id, start_date, end_date):
    """
    Generate compliance report for audit logs
    
    Args:
        company_id: Company ID
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    """
    try:
        from django.utils.dateparse import parse_datetime
        
        start = parse_datetime(start_date)
        end = parse_datetime(end_date)
        
        logs = AuditLog.objects.filter(
            company_id=company_id,
            timestamp__gte=start,
            timestamp__lte=end
        ).select_related('user', 'company')
        
        # Generate compliance report
        report_data = {
            'total_events': logs.count(),
            'by_action': {},
            'by_user': {},
            'critical_events': [],
        }
        
        for log in logs:
            # Count by action
            action = log.action
            report_data['by_action'][action] = report_data['by_action'].get(action, 0) + 1
            
            # Count by user
            user = log.user.username if log.user else 'System'
            report_data['by_user'][user] = report_data['by_user'].get(user, 0) + 1
            
            # Identify critical events
            if action in ['delete', 'assign', 'transfer_admin_decision']:
                report_data['critical_events'].append({
                    'timestamp': log.timestamp.isoformat(),
                    'user': user,
                    'action': action,
                    'description': log.description,
                })
        
        logger.info(f"Compliance report generated for company {company_id}: {report_data['total_events']} events")
        
        return report_data
        
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}", exc_info=True)
        return None
