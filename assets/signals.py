"""
Django Signals for Asset Management System

Event-driven architecture for:
- Asset lifecycle events
- Maintenance workflows
- Transfer approvals
- Audit logging

Following best practices from ServiceNow ITAM, IBM Maximo, SAP EAM
"""

import logging
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Asset, AssetTransfer, MaintenanceRecord
from audit.utils import log_audit

logger = logging.getLogger(__name__)


# ==========================
# Asset Signals
# ==========================

@receiver(post_save, sender=Asset)
def asset_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle asset creation and updates
    
    Triggers:
    - QR code generation (async)
    - Notification to admins (async)
    - Audit logging
    - Cache invalidation
    """
    try:
        if created:
            # Asset created
            logger.info(f"Asset created: {instance.uuid} - {instance.category.name if instance.category else 'No category'}")
            
            # Trigger async QR code generation if not already generated
            if not instance.qr_code:
                from .tasks import generate_qr_code_async
                generate_qr_code_async.delay(instance.id, instance.company_id)
            
            # Notify admins of new asset (async)
            from .tasks import send_asset_creation_notification
            send_asset_creation_notification.delay(instance.id, instance.company_id)
            
        else:
            # Asset updated
            logger.info(f"Asset updated: {instance.uuid}")
            
            # Check for status changes
            if hasattr(instance, '_original_status') and instance._original_status != instance.status:
                logger.info(f"Asset status changed: {instance._original_status} → {instance.status}")
                
                # Trigger status change notifications (async)
                from .tasks import send_asset_status_change_notification
                send_asset_status_change_notification.delay(
                    instance.id,
                    instance.company_id,
                    instance._original_status,
                    instance.status
                )
                
    except Exception as e:
        logger.error(f"Error in asset_post_save_handler: {e}", exc_info=True)


@receiver(pre_delete, sender=Asset)
def asset_pre_delete_handler(sender, instance, **kwargs):
    """
    Handle asset deletion (soft delete)
    
    Triggers:
    - Archive attachments (async)
    - Cancel pending transfers
    - Cancel pending maintenance
    - Audit logging
    """
    try:
        logger.info(f"Asset being deleted: {instance.uuid}")
        
        # Cancel pending transfers
        pending_transfers = AssetTransfer.objects.filter(
            asset=instance,
            state__in=['pending_receiver', 'receiver_approved', 'awaiting_admin']
        )
        for transfer in pending_transfers:
            transfer.state = 'cancelled'
            transfer.save()
            logger.info(f"Cancelled transfer {transfer.id} for deleted asset {instance.uuid}")
        
        # Cancel pending maintenance
        pending_maintenance = MaintenanceRecord.objects.filter(
            asset=instance,
            status__in=['scheduled', 'in_progress']
        )
        for maintenance in pending_maintenance:
            maintenance.status = 'cancelled'
            maintenance.save()
            logger.info(f"Cancelled maintenance {maintenance.id} for deleted asset {instance.uuid}")
            
    except Exception as e:
        logger.error(f"Error in asset_pre_delete_handler: {e}", exc_info=True)


# ==========================
# Asset Transfer Signals
# ==========================

@receiver(post_save, sender=AssetTransfer)
def asset_transfer_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle asset transfer state changes
    
    Triggers:
    - Notification to receiver (on creation)
    - Notification to admin (on receiver approval)
    - Notification to all parties (on completion)
    - Alert creation
    - Audit logging
    """
    try:
        if created:
            # Transfer initiated
            logger.info(f"Transfer initiated: {instance.id} - Asset {instance.asset.uuid}")
            
            # Notify receiver (async)
            from .tasks import send_transfer_notification
            send_transfer_notification.delay(
                instance.id,
                instance.company_id,
                'receiver',
                'pending_receiver'
            )
            
        else:
            # Transfer state changed
            logger.info(f"Transfer {instance.id} state changed to: {instance.state}")
            
            # Notify based on state
            if instance.state == 'receiver_approved':
                # Notify admin for final approval
                from .tasks import send_transfer_notification
                send_transfer_notification.delay(
                    instance.id,
                    instance.company_id,
                    'admin',
                    'awaiting_admin'
                )
                
            elif instance.state == 'completed':
                # Notify all parties of completion
                from .tasks import send_transfer_completion_notification
                send_transfer_completion_notification.delay(
                    instance.id,
                    instance.company_id
                )
                
            elif instance.state in ['receiver_rejected', 'cancelled']:
                # Notify initiator of rejection/cancellation
                from .tasks import send_transfer_rejection_notification
                send_transfer_rejection_notification.delay(
                    instance.id,
                    instance.company_id,
                    instance.state
                )
                
    except Exception as e:
        logger.error(f"Error in asset_transfer_post_save_handler: {e}", exc_info=True)


# ==========================
# Maintenance Record Signals
# ==========================

@receiver(post_save, sender=MaintenanceRecord)
def maintenance_record_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle maintenance record creation and updates
    
    Triggers:
    - Notification to assigned technician
    - Notification to supervisor
    - Asset status update
    - Audit logging
    """
    try:
        if created:
            # Maintenance scheduled
            logger.info(f"Maintenance scheduled: {instance.id} - Asset {instance.asset.uuid}")
            
            # Send reminder email (async, scheduled for 7 days before due date)
            if instance.scheduled_date and instance.status == 'scheduled':
                from .tasks import schedule_maintenance_reminder
                schedule_maintenance_reminder.delay(
                    instance.id,
                    instance.company_id
                )
                
        else:
            # Maintenance status changed
            logger.info(f"Maintenance {instance.id} status changed to: {instance.status}")
            
            if instance.status == 'in_progress':
                # Notify supervisor that maintenance started
                from .tasks import send_maintenance_notification
                send_maintenance_notification.delay(
                    instance.id,
                    instance.company_id,
                    'started'
                )
                
            elif instance.status == 'completed':
                # Notify stakeholders of completion
                from .tasks import send_maintenance_notification
                send_maintenance_notification.delay(
                    instance.id,
                    instance.company_id,
                    'completed'
                )
                
            elif instance.status == 'cancelled':
                # Notify stakeholders of cancellation
                from .tasks import send_maintenance_notification
                send_maintenance_notification.delay(
                    instance.id,
                    instance.company_id,
                    'cancelled'
                )
                
    except Exception as e:
        logger.error(f"Error in maintenance_record_post_save_handler: {e}", exc_info=True)


# ==========================
# Signal Utilities
# ==========================

def connect_signals():
    """
    Explicitly connect all signals
    Called from apps.py ready() method
    """
    logger.info("Connecting asset management signals...")
    # Signals are auto-connected via @receiver decorator
    # This function is for explicit connection if needed
    pass


def disconnect_signals():
    """
    Disconnect all signals (useful for testing)
    """
    logger.info("Disconnecting asset management signals...")
    post_save.disconnect(asset_post_save_handler, sender=Asset)
    pre_delete.disconnect(asset_pre_delete_handler, sender=Asset)
    post_save.disconnect(asset_transfer_post_save_handler, sender=AssetTransfer)
    post_save.disconnect(maintenance_record_post_save_handler, sender=MaintenanceRecord)
