"""
Celery Configuration for Enterprise Asset Management System

This module configures Celery for async task processing with:
- Multi-tenancy support
- Task prioritization
- Error handling and retries
- Result backend
- Monitoring integration

Following best practices from ServiceNow ITAM, IBM Maximo, SAP EAM
"""

import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')

# Create Celery app
app = Celery('assetms')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# Celery Beat Schedule (Periodic Tasks)
app.conf.beat_schedule = {
    # Daily Tasks
    'check-overdue-maintenance': {
        'task': 'assets.tasks.check_overdue_maintenance_all_companies',
        'schedule': crontab(hour=6, minute=0),  # 6 AM daily
        'options': {'queue': 'maintenance'},
    },
    'send-maintenance-reminders': {
        'task': 'assets.tasks.send_maintenance_reminders',
        'schedule': crontab(hour=8, minute=0),  # 8 AM daily
        'options': {'queue': 'notifications'},
    },
    'cleanup-soft-deleted-assets': {
        'task': 'assets.tasks.cleanup_soft_deleted_assets_all_companies',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'options': {'queue': 'cleanup'},
    },
    'cleanup-expired-sessions': {
        'task': 'users.tasks.cleanup_expired_sessions',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
        'options': {'queue': 'cleanup'},
    },
    
    # Weekly Tasks
    'archive-old-audit-logs': {
        'task': 'audit.tasks.archive_old_audit_logs',
        'schedule': crontab(day_of_week=0, hour=1, minute=0),  # Sunday 1 AM
        'options': {'queue': 'cleanup'},
    },
    'generate-weekly-reports': {
        'task': 'reports.tasks.generate_weekly_summary_reports',
        'schedule': crontab(day_of_week=1, hour=7, minute=0),  # Monday 7 AM
        'options': {'queue': 'reports'},
    },
    
    # Monthly Tasks
    'cleanup-orphaned-files': {
        'task': 'assets.tasks.cleanup_orphaned_files',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),  # 1st of month
        'options': {'queue': 'cleanup'},
    },
}


# Task routing (priority queues)
app.conf.task_routes = {
    # High priority - notifications
    'assets.tasks.send_transfer_notification': {'queue': 'notifications'},
    'assets.tasks.send_maintenance_notification': {'queue': 'notifications'},
    'tenancy.tasks.send_approval_notification': {'queue': 'notifications'},
    
    # Medium priority - reports
    'reports.tasks.generate_asset_report_async': {'queue': 'reports'},
    'reports.tasks.generate_excel_report_async': {'queue': 'reports'},
    
    # Low priority - cleanup
    'assets.tasks.cleanup_soft_deleted_assets': {'queue': 'cleanup'},
    'audit.tasks.archive_old_audit_logs': {'queue': 'cleanup'},
    
    # Maintenance tasks
    'assets.tasks.check_overdue_maintenance': {'queue': 'maintenance'},
    'assets.tasks.send_maintenance_reminders': {'queue': 'maintenance'},
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery configuration"""
    print(f'Request: {self.request!r}')
