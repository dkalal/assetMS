from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from assets.models import Asset, AssetTransfer
from audit.utils import ASSIGN_ACTION, log_audit
from tenancy.models import Alert, Branch


@dataclass
class TransferNotification:
    recipient_id: int
    level: str
    message: str
    context: Dict[str, Any]


def _build_context(transfer: AssetTransfer, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    asset = transfer.asset
    context = {
        "transfer_id": transfer.pk,
        "asset_id": asset.pk,
        "asset_uuid": str(asset.uuid),
        "asset_status": asset.status,
        "from_user_id": transfer.from_user_id,
        "to_user_id": transfer.to_user_id,
        "from_branch_id": transfer.from_branch_id,
        "to_branch_id": transfer.to_branch_id,
        "state": transfer.state,
    }
    if extra:
        context.update(extra)
    return context


def _create_alerts(company_id: int, branch_id: Optional[int], notifications: Iterable[TransferNotification]) -> None:
    alerts = [
        Alert(
            company_id=company_id,
            branch_id=branch_id,
            recipient_id=notification.recipient_id,
            level=notification.level,
            message=notification.message,
            context=notification.context,
        )
        for notification in notifications
    ]
    Alert.objects.bulk_create(alerts)


def _validate_tenancy(expected_company_id: int, *, to_user_company_id: Optional[int], branch: Optional[Branch]) -> None:
    if to_user_company_id is not None and to_user_company_id != expected_company_id:
        raise ValidationError("Target user must belong to the same company as the asset.")
    if branch and branch.company_id != expected_company_id:
        raise ValidationError("Branch must belong to the same company as the asset.")


def initiate_transfer(
    *,
    initiator,
    asset: Asset,
    to_user,
    to_branch: Optional[Branch] = None,
    initiator_comment: str = "",
    force_transfer: bool = False,
    context: Optional[Dict[str, Any]] = None,
) -> AssetTransfer:
    """
    Create a new transfer request for an asset and notify the intended recipient.
    
    WORLD-CLASS: Handles assets in maintenance status intelligently.
    - Default: Blocks transfer, provides guidance to complete maintenance first
    - Override: Allows admin to force transfer with proper documentation
    - Audit: Complete trail of decision and reasoning
    
    Args:
        force_transfer: If True, allows transfer of asset in maintenance (admin only, requires detailed reason)
    """

    if asset.company_id is None:
        raise ValidationError("Asset must belong to a company before transfer can be initiated.")
    if initiator.company_id != asset.company_id:
        raise PermissionDenied("Initiator cannot transfer assets outside their company scope.")
    if getattr(to_user, "company_id", asset.company_id) != asset.company_id:
        raise ValidationError("Recipient must belong to the same company as the asset.")
    _validate_tenancy(asset.company_id, to_user_company_id=getattr(to_user, "company_id", None), branch=to_branch)
    
    # Check cross-branch transfer policy
    from tenancy.policy_service import policy_service
    policy_service.validate_cross_branch_transfer(asset.company, asset.branch, to_branch)

    if AssetTransfer.objects.filter(asset=asset, state__in=AssetTransfer.ACTIVE_STATES).exists():
        raise ValidationError("An active transfer already exists for this asset.")
    
    # WORLD-CLASS: Validate asset status for transfer (handle in_maintenance intelligently)
    if asset.status == Asset.STATUS_IN_MAINTENANCE:
        from assets.models import MaintenanceRecord
        active_maintenance = MaintenanceRecord.objects.filter(
            asset=asset,
            status=MaintenanceRecord.Status.IN_PROGRESS
        ).select_related('performed_by', 'supervisor').first()
        
        if active_maintenance and not force_transfer:
            # Build detailed error with guidance
            error_msg = (
                f"Asset '{asset}' is currently undergoing maintenance. "
                f"Maintenance Type: {active_maintenance.get_maintenance_type_display()}. "
                f"Started: {active_maintenance.started_at.strftime('%Y-%m-%d %H:%M')}. "
                f"Performed by: {active_maintenance.performed_by.get_full_name() if active_maintenance.performed_by else 'Unassigned'}. "
                f"\n\nRecommended actions:\n"
                f"1. Complete the maintenance work first (recommended)\n"
                f"2. Cancel the maintenance if no longer needed\n"
                f"3. Force transfer if urgent (admin only, requires detailed reason)"
            )
            raise ValidationError({
                'asset': [error_msg],
                'maintenance_uuid': str(active_maintenance.uuid),
                'can_force': getattr(initiator, 'role', None) in ['admin'] or initiator.is_superuser,
            })
        
        # If force_transfer=True, require detailed reason
        if force_transfer:
            if not initiator_comment or len(initiator_comment.strip()) < 20:
                raise ValidationError(
                    "Force transfer of asset in maintenance requires detailed reason (minimum 20 characters). "
                    "Explain why transfer cannot wait for maintenance completion."
                )
            
            # Verify user has permission to force transfer
            if getattr(initiator, 'role', None) not in ['admin'] and not initiator.is_superuser:
                raise PermissionDenied("Only admins can force transfer of assets in maintenance.")
            
            # Log the force transfer decision
            log_audit(
                initiator,
                "transfer_force_in_maintenance",
                asset,
                f"Force transfer initiated while asset in maintenance. Reason: {initiator_comment}",
                company=asset.company,
                branch=asset.branch,
                metadata={
                    'force_transfer': True,
                    'asset_status': asset.status,
                    'maintenance_uuid': str(active_maintenance.uuid) if active_maintenance else None,
                    'initiator_comment': initiator_comment,
                    'to_user': to_user.username,
                    'to_branch': to_branch.name if to_branch else None,
                },
            )

    from_user = asset.assigned_to
    from_branch = asset.branch

    with transaction.atomic():
        # WORLD-CLASS FIX: Set asset to TRANSFERRED status during transfer process
        # This temporarily blocks operations until transfer completes
        # Inspired by ServiceNow ITAM, IBM Maximo, SAP EAM
        previous_status = asset.status
        asset.status = Asset.STATUS_TRANSFERRED
        asset.save(update_fields=['status', 'updated_at'])
        
        transfer = AssetTransfer.objects.create(
            company_id=asset.company_id,
            asset=asset,
            initiator=initiator,
            from_user=from_user,
            to_user=to_user,
            from_branch=from_branch,
            to_branch=to_branch,
            reason=initiator_comment,
            context=context or {},
        )

        log_audit(
            initiator,
            "transfer_initiated",
            asset,
            f"Transfer initiated for asset to {to_user}. Status: {previous_status} → transferred. Comment: {initiator_comment}".strip(),
            company=asset.company,
            branch=from_branch,
            related_user=to_user,
            metadata={
                'previous_status': previous_status,
                'new_status': Asset.STATUS_TRANSFERRED,
                'transfer_id': transfer.pk,
            },
        )

        notifications = [
            TransferNotification(
                recipient_id=to_user.id,
                level=Alert.LEVEL_WARNING,
                message=f"Asset transfer request for {asset} awaits your approval.",
                context=_build_context(
                    transfer,
                    {
                        "initiator_id": initiator.id,
                        "initiator_comment": initiator_comment,
                    },
                ),
            )
        ]
        _create_alerts(asset.company_id, to_branch.pk if to_branch else None, notifications)

    return transfer


def receiver_review(
    *,
    transfer: AssetTransfer,
    receiver,
    decision: str,
    comment: str = "",
) -> AssetTransfer:
    """Allow the designated recipient to approve or reject the transfer."""

    if transfer.to_user_id != receiver.id:
        raise PermissionDenied("Only the designated recipient can respond to this transfer.")
    if transfer.state != AssetTransfer.TransferState.PENDING_RECEIVER:
        raise ValidationError("This transfer is not awaiting receiver action.")
    if decision not in AssetTransfer.Decision.values:
        raise ValidationError("Unsupported receiver decision supplied.")

    with transaction.atomic():
        transfer.receiver_decision = decision
        transfer.receiver_comment = comment
        transfer.receiver_decided_at = timezone.now()

        asset = transfer.asset
        
        if decision == AssetTransfer.Decision.APPROVED:
            transfer.state = AssetTransfer.TransferState.AWAITING_ADMIN
            status_message = "Receiver approved the transfer. Awaiting admin review."
        else:
            # WORLD-CLASS FIX: Restore asset to ACTIVE when receiver rejects
            # Transfer is cancelled, asset returns to normal operations
            asset.status = Asset.STATUS_ACTIVE
            asset.save(update_fields=['status', 'updated_at'])
            
            transfer.state = AssetTransfer.TransferState.RECEIVER_REJECTED
            status_message = "Receiver rejected the transfer request. Asset status restored to active."

        transfer.save(update_fields=[
            "receiver_decision",
            "receiver_comment",
            "receiver_decided_at",
            "state",
            "updated_at",
        ])

        log_audit(
            receiver,
            "transfer_receiver_decision",
            transfer.asset,
            status_message + (f" Comment: {comment}" if comment else ""),
            company=transfer.company,
            branch=transfer.to_branch or transfer.from_branch,
            related_user=transfer.initiator,
            metadata={
                'decision': decision,
                'transfer_id': transfer.pk,
                'status_restored': decision == AssetTransfer.Decision.REJECTED,
            } if decision == AssetTransfer.Decision.REJECTED else None,
        )

        notifications = [
            TransferNotification(
                recipient_id=transfer.initiator_id,
                level=Alert.LEVEL_INFO if decision == AssetTransfer.Decision.APPROVED else Alert.LEVEL_ERROR,
                message=f"Receiver {decision} the asset transfer for {transfer.asset}.",
                context=_build_context(
                    transfer,
                    {
                        "receiver_comment": comment,
                    },
                ),
            )
        ]

        if transfer.from_user_id and transfer.from_user_id != transfer.initiator_id:
            notifications.append(
                TransferNotification(
                    recipient_id=transfer.from_user_id,
                    level=Alert.LEVEL_INFO,
                    message=f"Transfer request for {transfer.asset} is {decision} by the recipient.",
                    context=_build_context(transfer),
                )
            )

        _create_alerts(transfer.company_id, transfer.to_branch_id, notifications)

    return transfer


def admin_review(
    *,
    transfer: AssetTransfer,
    reviewer,
    decision: str,
    comment: str = "",
) -> AssetTransfer:
    """Finalize transfer after administrative review, reassigning the asset as needed."""

    if getattr(reviewer, "role", "user") not in {"admin", "manager"}:
        raise PermissionDenied("Only administrators or managers can review transfers.")
    if reviewer.company_id != transfer.company_id:
        raise PermissionDenied("Reviewer cannot approve transfers outside their company scope.")
    if transfer.state not in {
        AssetTransfer.TransferState.AWAITING_ADMIN,
        AssetTransfer.TransferState.RECEIVER_APPROVED,
    }:
        raise ValidationError("Transfer is not awaiting administrative review.")
    if decision not in AssetTransfer.Decision.values:
        raise ValidationError("Unsupported admin decision supplied.")

    with transaction.atomic():
        transfer.admin_decision = decision
        transfer.admin_comment = comment
        transfer.admin_decided_at = timezone.now()

        asset = transfer.asset
        update_fields = []

        if decision == AssetTransfer.Decision.APPROVED:
            transfer.state = AssetTransfer.TransferState.COMPLETED
            previous_assignee = asset.assigned_to
            previous_status = asset.status
            asset.assigned_to = transfer.to_user
            if transfer.to_branch_id:
                asset.branch_id = transfer.to_branch_id
                update_fields.append("branch")
            
            # WORLD-CLASS: Handle asset in maintenance during transfer
            # Check if asset was in maintenance when transferred
            was_in_maintenance = (previous_status == Asset.STATUS_IN_MAINTENANCE)
            
            if was_in_maintenance:
                # Keep asset in maintenance status, update maintenance record
                from assets.models import MaintenanceRecord
                active_maintenance = MaintenanceRecord.objects.filter(
                    asset=asset,
                    status=MaintenanceRecord.Status.IN_PROGRESS
                ).first()
                
                if active_maintenance:
                    # Update maintenance record with new branch/owner context
                    active_maintenance.branch = asset.branch
                    # Add note about transfer
                    transfer_note = (
                        f"\n\n[TRANSFER DURING MAINTENANCE]\n"
                        f"Asset transferred from {previous_assignee} to {transfer.to_user} "
                        f"on {timezone.now().strftime('%Y-%m-%d %H:%M')}.\n"
                        f"Maintenance continues under new ownership."
                    )
                    active_maintenance.notes = (active_maintenance.notes or '') + transfer_note
                    active_maintenance.save(update_fields=['branch', 'notes', 'updated_at'])
                    
                    # Notify maintenance supervisor
                    if active_maintenance.supervisor:
                        Alert.objects.create(
                            company=asset.company,
                            branch=asset.branch,
                            recipient=active_maintenance.supervisor,
                            level=Alert.LEVEL_WARNING,
                            message=f"Asset {asset} was transferred while under maintenance. Please coordinate with new owner {transfer.to_user.get_full_name()}.",
                            context={
                                'asset_id': asset.pk,
                                'transfer_id': transfer.pk,
                                'maintenance_uuid': str(active_maintenance.uuid),
                                'new_owner': transfer.to_user.get_full_name(),
                                'new_owner_id': transfer.to_user.pk,
                            }
                        )
                    
                    # Asset remains in maintenance status
                    asset.status = Asset.STATUS_IN_MAINTENANCE
                else:
                    # No active maintenance found, restore to active
                    asset.status = Asset.STATUS_ACTIVE
            else:
                # Normal transfer: Restore asset to ACTIVE status
                # Asset is now ready for use by new owner (can perform maintenance, etc.)
                # Matches ServiceNow ITAM, IBM Maximo, SAP EAM behavior
                asset.status = Asset.STATUS_ACTIVE
            
            update_fields.extend(["assigned_to", "status", "updated_at"])
            asset.save(update_fields=update_fields)

            transfer.approved_by = reviewer
            transfer.save(update_fields=[
                "admin_decision",
                "admin_comment",
                "admin_decided_at",
                "state",
                "approved_by",
                "updated_at",
            ])

            # Build audit log message based on final status
            if was_in_maintenance and asset.status == Asset.STATUS_IN_MAINTENANCE:
                status_msg = f"Status: transferred → in_maintenance (maintenance continues)"
                audit_metadata = {
                    'previous_status': Asset.STATUS_TRANSFERRED,
                    'new_status': Asset.STATUS_IN_MAINTENANCE,
                    'transfer_id': transfer.pk,
                    'previous_assignee': previous_assignee.username if previous_assignee else None,
                    'new_assignee': transfer.to_user.username,
                    'maintenance_continues': True,
                    'maintenance_uuid': str(active_maintenance.uuid) if active_maintenance else None,
                }
            else:
                status_msg = f"Status: transferred → active"
                audit_metadata = {
                    'previous_status': Asset.STATUS_TRANSFERRED,
                    'new_status': Asset.STATUS_ACTIVE,
                    'transfer_id': transfer.pk,
                    'previous_assignee': previous_assignee.username if previous_assignee else None,
                    'new_assignee': transfer.to_user.username,
                }
            
            log_audit(
                reviewer,
                ASSIGN_ACTION,
                asset,
                f"Transfer completed. Asset reassigned to {transfer.to_user}. {status_msg}.",
                company=transfer.company,
                branch=transfer.to_branch or transfer.from_branch or asset.branch,
                related_user=transfer.to_user,
                metadata=audit_metadata,
            )

            if previous_assignee and previous_assignee != transfer.to_user:
                log_audit(
                    reviewer,
                    "transfer_unassign",
                    asset,
                    f"Asset unassigned from {previous_assignee} as part of transfer.",
                    company=transfer.company,
                    branch=transfer.from_branch or asset.branch,
                    related_user=previous_assignee,
                )
        else:
            # WORLD-CLASS FIX: Restore asset to ACTIVE when transfer is rejected
            # Asset returns to normal operations
            asset.status = Asset.STATUS_ACTIVE
            asset.save(update_fields=['status', 'updated_at'])
            
            transfer.state = AssetTransfer.TransferState.CANCELLED
            transfer.save(update_fields=[
                "admin_decision",
                "admin_comment",
                "admin_decided_at",
                "state",
                "updated_at",
            ])
            log_audit(
                reviewer,
                "transfer_admin_rejected",
                asset,
                f"Transfer rejected by admin. Status restored to active. Comment: {comment}",
                company=transfer.company,
                branch=transfer.from_branch or asset.branch,
                related_user=transfer.initiator,
                metadata={
                    'previous_status': Asset.STATUS_TRANSFERRED,
                    'new_status': Asset.STATUS_ACTIVE,
                    'transfer_id': transfer.pk,
                },
            )

        level = Alert.LEVEL_SUCCESS if decision == AssetTransfer.Decision.APPROVED else Alert.LEVEL_ERROR
        notifications = [
            TransferNotification(
                recipient_id=transfer.initiator_id,
                level=level,
                message=f"Transfer for {asset} was {decision} by admin.",
                context=_build_context(
                    transfer,
                    {
                        "admin_comment": comment,
                        "admin_id": reviewer.id,
                    },
                ),
            ),
            TransferNotification(
                recipient_id=transfer.to_user_id,
                level=level,
                message=f"Admin {decision} the transfer for {asset}.",
                context=_build_context(
                    transfer,
                    {
                        "admin_comment": comment,
                        "admin_id": reviewer.id,
                    },
                ),
            ),
        ]
        if transfer.from_user_id and transfer.from_user_id not in {transfer.initiator_id, transfer.to_user_id}:
            notifications.append(
                TransferNotification(
                    recipient_id=transfer.from_user_id,
                    level=level,
                    message=f"Admin {decision} the transfer for {asset}.",
                    context=_build_context(transfer),
                )
            )

        _create_alerts(transfer.company_id, transfer.to_branch_id, notifications)

    return transfer


__all__ = [
    "initiate_transfer",
    "receiver_review",
    "admin_review",
]
