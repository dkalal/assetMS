"""
Celery Tasks for Asset Management

Async tasks for:
- Notifications (email, SMS)
- Report generation
- Maintenance scheduling
- Data cleanup
- QR code generation

Following best practices from ServiceNow ITAM, IBM Maximo, SAP EAM
"""

import logging
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.template.loader import render_to_string

from .models import Asset, AssetTransfer, MaintenanceRecord
from tenancy.models import Alert, Company
from users.models import User
from audit.utils import log_audit

logger = logging.getLogger(__name__)


# ==========================
# Notification Tasks
# ==========================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification(self, user_id, subject, message, company_id, html_message=None):
    """
    Send email notification to user
    
    Args:
        user_id: User ID to send email to
        subject: Email subject
        message: Plain text message
        company_id: Company ID for multi-tenancy
        html_message: Optional HTML message
        
    Returns:
        bool: True if sent successfully
    """
    try:
        # Validate company context
        user = User.objects.select_related('company').get(id=user_id, company_id=company_id)
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email sent to {user.email}: {subject}")
        return True
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for company {company_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)


@shared_task(bind=True)
def send_transfer_notification(self, transfer_id, company_id, recipient_role, state):
    """
    Send transfer approval notification
    
    Args:
        transfer_id: AssetTransfer ID
        company_id: Company ID for multi-tenancy
        recipient_role: 'receiver', 'admin', or 'all'
        state: Transfer state
    """
    try:
        # Get transfer with company validation
        transfer = AssetTransfer.objects.select_related(
            'asset', 'company', 'from_branch', 'to_branch', 'initiated_by'
        ).get(id=transfer_id, company_id=company_id)
        
        # Determine recipients
        if recipient_role == 'receiver':
            recipients = [transfer.assigned_to] if transfer.assigned_to else []
        elif recipient_role == 'admin':
            recipients = User.objects.filter(company_id=company_id, role='admin')
        else:
            recipients = User.objects.filter(
                company_id=company_id,
                role__in=['admin', 'manager']
            )
        
        # Send notifications
        for user in recipients:
            # Create in-app alert
            Alert.objects.create(
                company_id=company_id,
                user=user,
                level=Alert.LEVEL_INFO,
                title=f"Asset Transfer: {transfer.asset.category.name if transfer.asset.category else 'Asset'}",
                message=f"Transfer from {transfer.from_branch.name} to {transfer.to_branch.name} - {state}",
                context={
                    'transfer_id': transfer.id,
                    'asset_id': transfer.asset.id,
                    'state': state,
                }
            )
            
            # Send email (async)
            if user.email:
                send_email_notification.delay(
                    user.id,
                    f"[{transfer.company.name}] Asset Transfer Notification",
                    f"Transfer of {transfer.asset.category.name if transfer.asset.category else 'Asset'} requires your attention.",
                    company_id
                )
        
        logger.info(f"Transfer notifications sent for transfer {transfer_id}")
        
    except AssetTransfer.DoesNotExist:
        logger.error(f"Transfer {transfer_id} not found for company {company_id}")
    except Exception as e:
        logger.error(f"Error sending transfer notification: {e}", exc_info=True)


@shared_task(bind=True)
def send_transfer_completion_notification(self, transfer_id, company_id):
    """Send notification when transfer is completed"""
    try:
        transfer = AssetTransfer.objects.select_related(
            'asset', 'company', 'initiated_by', 'assigned_to'
        ).get(id=transfer_id, company_id=company_id)
        
        # Notify initiator and receiver
        recipients = [transfer.initiated_by]
        if transfer.assigned_to:
            recipients.append(transfer.assigned_to)
        
        for user in recipients:
            Alert.objects.create(
                company_id=company_id,
                user=user,
                level=Alert.LEVEL_SUCCESS,
                title="Transfer Completed",
                message=f"Transfer of {transfer.asset.category.name if transfer.asset.category else 'Asset'} completed successfully",
                context={'transfer_id': transfer.id}
            )
            
    except Exception as e:
        logger.error(f"Error sending transfer completion notification: {e}", exc_info=True)


@shared_task(bind=True)
def send_transfer_rejection_notification(self, transfer_id, company_id, state):
    """Send notification when transfer is rejected/cancelled"""
    try:
        transfer = AssetTransfer.objects.select_related(
            'asset', 'company', 'initiated_by'
        ).get(id=transfer_id, company_id=company_id)
        
        Alert.objects.create(
            company_id=company_id,
            user=transfer.initiated_by,
            level=Alert.LEVEL_WARNING,
            title="Transfer Rejected",
            message=f"Transfer of {transfer.asset.category.name if transfer.asset.category else 'Asset'} was {state}",
            context={'transfer_id': transfer.id, 'state': state}
        )
        
    except Exception as e:
        logger.error(f"Error sending transfer rejection notification: {e}", exc_info=True)


@shared_task(bind=True)
def send_maintenance_notification(self, maintenance_id, company_id, event_type):
    """
    Send maintenance event notification
    
    Args:
        maintenance_id: MaintenanceRecord ID
        company_id: Company ID
        event_type: 'started', 'completed', 'cancelled', 'overdue'
    """
    try:
        maintenance = MaintenanceRecord.objects.select_related(
            'asset', 'company', 'performed_by', 'supervisor'
        ).get(id=maintenance_id, company_id=company_id)
        
        # Determine recipients
        recipients = []
        if maintenance.supervisor:
            recipients.append(maintenance.supervisor)
        if maintenance.performed_by:
            recipients.append(maintenance.performed_by)
        
        # Add admins for overdue maintenance
        if event_type == 'overdue':
            admins = User.objects.filter(company_id=company_id, role='admin')
            recipients.extend(admins)
        
        # Send notifications
        level = Alert.LEVEL_WARNING if event_type == 'overdue' else Alert.LEVEL_INFO
        for user in recipients:
            Alert.objects.create(
                company_id=company_id,
                user=user,
                level=level,
                title=f"Maintenance {event_type.title()}",
                message=f"Maintenance for {maintenance.asset.category.name if maintenance.asset.category else 'Asset'} - {event_type}",
                context={'maintenance_id': maintenance.id, 'event_type': event_type}
            )
        
        logger.info(f"Maintenance notifications sent for {maintenance_id}")
        
    except Exception as e:
        logger.error(f"Error sending maintenance notification: {e}", exc_info=True)


@shared_task(bind=True)
def send_asset_creation_notification(self, asset_id, company_id):
    """Notify admins of new asset creation"""
    try:
        asset = Asset.objects.select_related('company', 'category').get(
            id=asset_id, company_id=company_id
        )
        
        admins = User.objects.filter(company_id=company_id, role='admin')
        
        for admin in admins:
            Alert.objects.create(
                company_id=company_id,
                user=admin,
                level=Alert.LEVEL_INFO,
                title="New Asset Created",
                message=f"New {asset.category.name if asset.category else 'Asset'} added to inventory",
                context={'asset_id': asset.id}
            )
        
    except Exception as e:
        logger.error(f"Error sending asset creation notification: {e}", exc_info=True)


@shared_task(bind=True)
def send_asset_status_change_notification(self, asset_id, company_id, old_status, new_status):
    """Notify stakeholders of asset status change"""
    try:
        asset = Asset.objects.select_related('company', 'assigned_to').get(
            id=asset_id, company_id=company_id
        )
        
        # Notify assigned user if exists
        if asset.assigned_to:
            Alert.objects.create(
                company_id=company_id,
                user=asset.assigned_to,
                level=Alert.LEVEL_INFO,
                title="Asset Status Changed",
                message=f"Asset status changed from {old_status} to {new_status}",
                context={'asset_id': asset.id, 'old_status': old_status, 'new_status': new_status}
            )
        
    except Exception as e:
        logger.error(f"Error sending asset status change notification: {e}", exc_info=True)


# ==========================
# QR Code Generation Tasks
# ==========================

@shared_task(bind=True, max_retries=2)
def generate_qr_code_async(self, asset_id, company_id):
    """
    Generate QR code for asset asynchronously
    
    Args:
        asset_id: Asset ID
        company_id: Company ID for multi-tenancy
    """
    try:
        import qrcode
        from io import BytesIO
        from django.core.files.base import ContentFile
        
        # Get asset with company validation
        asset = Asset.objects.select_related('company').get(
            id=asset_id, company_id=company_id
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr_data = f"{settings.ALLOWED_HOSTS[0]}/assets/{asset.uuid}/"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        # Save to asset
        filename = f"qr_{asset.uuid}.png"
        asset.qr_code.save(filename, ContentFile(buffer.getvalue()), save=True)
        
        logger.info(f"QR code generated for asset {asset.uuid}")
        
    except Asset.DoesNotExist:
        logger.error(f"Asset {asset_id} not found for company {company_id}")
    except Exception as e:
        logger.error(f"Error generating QR code: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


# ==========================
# Maintenance Tasks
# ==========================

@shared_task(bind=True)
def check_overdue_maintenance_all_companies(self):
    """Check for overdue maintenance across all companies"""
    try:
        companies = Company.objects.all()
        
        for company in companies:
            check_overdue_maintenance.delay(company.id)
        
        logger.info(f"Scheduled overdue maintenance checks for {companies.count()} companies")
        
    except Exception as e:
        logger.error(f"Error scheduling overdue maintenance checks: {e}", exc_info=True)


@shared_task(bind=True)
def check_overdue_maintenance(self, company_id):
    """
    Check for overdue maintenance for a company
    
    Args:
        company_id: Company ID
    """
    try:
        today = timezone.now().date()
        
        # Find overdue maintenance
        overdue = MaintenanceRecord.objects.filter(
            company_id=company_id,
            status='scheduled',
            scheduled_date__lt=today
        ).select_related('asset', 'company')
        
        for maintenance in overdue:
            # Send overdue notification
            send_maintenance_notification.delay(
                maintenance.id,
                company_id,
                'overdue'
            )
        
        logger.info(f"Found {overdue.count()} overdue maintenance records for company {company_id}")
        
    except Exception as e:
        logger.error(f"Error checking overdue maintenance: {e}", exc_info=True)


@shared_task(bind=True)
def send_maintenance_reminders(self):
    """Send reminders for upcoming maintenance (7 days before due)"""
    try:
        reminder_date = timezone.now().date() + timedelta(days=7)
        
        upcoming = MaintenanceRecord.objects.filter(
            status='scheduled',
            scheduled_date=reminder_date
        ).select_related('asset', 'company', 'supervisor')
        
        for maintenance in upcoming:
            send_maintenance_notification.delay(
                maintenance.id,
                maintenance.company_id,
                'reminder'
            )
        
        logger.info(f"Sent {upcoming.count()} maintenance reminders")
        
    except Exception as e:
        logger.error(f"Error sending maintenance reminders: {e}", exc_info=True)


@shared_task(bind=True)
def schedule_maintenance_reminder(self, maintenance_id, company_id):
    """Schedule a reminder for specific maintenance"""
    try:
        maintenance = MaintenanceRecord.objects.get(
            id=maintenance_id, company_id=company_id
        )
        
        if maintenance.scheduled_date:
            reminder_date = maintenance.scheduled_date - timedelta(days=7)
            
            if reminder_date >= timezone.now().date():
                # Schedule reminder task
                send_maintenance_notification.apply_async(
                    args=[maintenance_id, company_id, 'reminder'],
                    eta=timezone.make_aware(timezone.datetime.combine(reminder_date, timezone.datetime.min.time()))
                )
                logger.info(f"Scheduled reminder for maintenance {maintenance_id}")
        
    except Exception as e:
        logger.error(f"Error scheduling maintenance reminder: {e}", exc_info=True)


# ==========================
# Cleanup Tasks
# ==========================

@shared_task(bind=True)
def cleanup_soft_deleted_assets_all_companies(self):
    """Cleanup soft-deleted assets across all companies"""
    try:
        companies = Company.objects.all()
        
        for company in companies:
            cleanup_soft_deleted_assets.delay(company.id, days=30)
        
        logger.info(f"Scheduled soft-delete cleanup for {companies.count()} companies")
        
    except Exception as e:
        logger.error(f"Error scheduling soft-delete cleanup: {e}", exc_info=True)


@shared_task(bind=True)
def cleanup_soft_deleted_assets(self, company_id, days=30):
    """
    Permanently delete soft-deleted assets after retention period
    
    Args:
        company_id: Company ID
        days: Retention period in days (default 30)
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find soft-deleted assets past retention period
        deleted_assets = Asset.objects.filter(
            company_id=company_id,
            status=Asset.STATUS_DELETED,
            updated_at__lt=cutoff_date
        )
        
        count = deleted_assets.count()
        
        # Permanently delete
        deleted_assets.delete()
        
        logger.info(f"Permanently deleted {count} assets for company {company_id}")
        
        # Audit log
        log_audit(
            user=None,  # System action
            action='cleanup',
            target=None,
            description=f"Permanently deleted {count} soft-deleted assets (30-day retention)",
            company_id=company_id,
            metadata={'count': count, 'retention_days': days}
        )
        
    except Exception as e:
        logger.error(f"Error cleaning up soft-deleted assets: {e}", exc_info=True)


@shared_task(bind=True)
def cleanup_orphaned_files(self):
    """Cleanup orphaned files (files not linked to any asset)"""
    try:
        # This task would scan media storage and remove files not referenced in database
        # Implementation depends on storage backend (local, S3, Cloudinary, etc.)
        logger.info("Orphaned file cleanup task executed")
        
    except Exception as e:
        logger.error(f"Error cleaning up orphaned files: {e}", exc_info=True)
