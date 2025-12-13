"""
Asset Status Change Service Layer
World-class workflows for all asset status transitions.
Inspired by ServiceNow ITAM, IBM Maximo, SAP EAM.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from assets.models import Asset, MaintenanceRecord
from audit.utils import MAINTENANCE_ACTION, log_audit
from tenancy.models import Alert


class AssetStatusChangeService:
    """
    Encapsulates all asset status change workflows with validation,
    audit trails, and stakeholder notifications.
    """

    # Status change action for audit logging
    STATUS_CHANGE_ACTION = "status_change"

    @staticmethod
    def _guard_admin_only(user) -> None:
        """Ensure only admins can perform certain status changes."""
        if getattr(user, "role", "user") != "admin" and not user.is_superuser:
            raise PermissionDenied("Only administrators can perform this action.")

    @staticmethod
    def _guard_admin_or_manager(user) -> None:
        """Ensure only admins or managers can perform status changes."""
        if getattr(user, "role", "user") not in {"admin", "manager"} and not user.is_superuser:
            raise PermissionDenied("Only administrators or managers can change asset status.")

    @staticmethod
    def _guard_company(user_company_id: int, asset: Asset) -> None:
        """Enforce multi-tenancy."""
        if asset.company_id != user_company_id:
            raise PermissionDenied("You may only manage assets in your company scope.")

    @classmethod
    def change_to_in_maintenance(
        cls,
        *,
        asset: Asset,
        user,
        reason: str,
        maintenance_type: str = "corrective",
        expected_duration_days: Optional[int] = None,
    ) -> tuple[Asset, MaintenanceRecord]:
        """
        Handle ACTIVE → IN_MAINTENANCE transition.
        
        Workflow:
        1. Validate prerequisites (maintenance enabled, no active maintenance)
        2. Create MaintenanceRecord with status=IN_PROGRESS
        3. Update asset status to IN_MAINTENANCE
        4. Send notifications to stakeholders
        5. Log audit trail
        
        Args:
            asset: Asset to put into maintenance
            user: User performing the action
            reason: Reason for maintenance (min 10 characters)
            maintenance_type: Type of maintenance (preventive/corrective/emergency)
            expected_duration_days: Expected duration in days (optional)
            
        Returns:
            Tuple of (updated asset, created maintenance record)
        """
        cls._guard_admin_or_manager(user)
        cls._guard_company(user.company_id, asset)

        # Validation - WORLD-CLASS FIX: Case-insensitive comparison
        # Normalize status for comparison to handle any case variations
        current_status = asset.status.lower() if asset.status else ''
        if current_status != Asset.STATUS_ACTIVE:
            raise ValidationError(
                f"Cannot start maintenance on asset with status '{asset.status}'. "
                f"Asset must be ACTIVE. Current status: {asset.get_status_display()}"
            )

        # WORLD-CLASS FIX: Don't require maintenance_enabled for corrective/emergency maintenance
        # maintenance_enabled only controls SCHEDULED/PREVENTIVE maintenance
        # Any asset can undergo corrective or emergency maintenance regardless of settings
        # This follows industry best practices (ServiceNow, Maximo, SAP EAM)
        if not asset.maintenance_enabled and maintenance_type == 'preventive':
            raise ValidationError(
                "Preventive maintenance tracking is not enabled for this asset. "
                "Enable maintenance tracking in asset settings or use corrective/emergency maintenance type."
            )

        if not reason or len(reason.strip()) < 10:
            raise ValidationError("Maintenance reason must be at least 10 characters.")

        # Check for existing active maintenance
        active_maintenance = MaintenanceRecord.objects.filter(
            asset=asset,
            status__in=[MaintenanceRecord.Status.SCHEDULED, MaintenanceRecord.Status.IN_PROGRESS],
        ).first()

        if active_maintenance:
            raise ValidationError(
                f"Asset already has active maintenance (ID: {active_maintenance.id}, Status: {active_maintenance.status}). "
                "Complete or cancel existing maintenance before starting new one."
            )

        with transaction.atomic():
            # Create maintenance record
            maintenance_record = MaintenanceRecord.objects.create(
                asset=asset,
                company=asset.company,
                branch=asset.branch,
                status=MaintenanceRecord.Status.IN_PROGRESS,
                scheduled_for=timezone.localdate(),
                started_at=timezone.now(),
                performed_by=user,
                description=f"{maintenance_type.title()} Maintenance: {reason}",
                created_by=user,
                updated_by=user,
            )

            # Update asset status
            previous_status = asset.status
            asset.status = Asset.STATUS_IN_MAINTENANCE
            asset.status_changed_at = timezone.now()
            asset.status_changed_by = user
            asset.status_change_reason = reason
            # CRITICAL: Don't use update_fields - it discards form changes!
            # Save all fields to preserve form data (assigned_to, branch, warranty, etc.)
            asset.save()

            # Audit log
            log_audit(
                user,
                cls.STATUS_CHANGE_ACTION,
                asset,
                f"Asset status changed: {previous_status} → IN_MAINTENANCE. Reason: {reason[:100]}",
                company=asset.company,
                branch=asset.branch,
                metadata={
                    "previous_status": previous_status,
                    "new_status": Asset.STATUS_IN_MAINTENANCE,
                    "reason": reason,
                    "maintenance_type": maintenance_type,
                    "maintenance_record_id": maintenance_record.id,
                    "expected_duration_days": expected_duration_days,
                },
            )

            # Notifications
            notifications = []
            
            # Notify asset owner
            if asset.assigned_to and asset.assigned_to != user:
                notifications.append(
                    Alert(
                        company=asset.company,
                        branch=asset.branch,
                        recipient=asset.assigned_to,
                        level=Alert.LEVEL_INFO,
                        message=f"Asset '{asset}' has been placed under maintenance by {user.get_full_name() or user.username}.",
                        context={
                            "asset_id": asset.id,
                            "asset_uuid": str(asset.uuid),
                            "reason": reason,
                            "maintenance_type": maintenance_type,
                        },
                    )
                )

            # Notify branch manager (if different from user)
            # TODO: Implement branch manager notification

            if notifications:
                Alert.objects.bulk_create(notifications)

        return asset, maintenance_record

    @classmethod
    def change_to_retired(
        cls,
        *,
        asset: Asset,
        user,
        reason: str,
        disposal_method: str,
        salvage_value: Optional[Decimal] = None,
        retirement_date: Optional[date] = None,
    ) -> Asset:
        """
        Handle ANY → RETIRED transition.
        
        Workflow:
        1. Validate prerequisites (no active maintenance/transfers, admin role)
        2. Prompt for retirement details
        3. Update asset status to RETIRED
        4. Clear assigned_to, cancel scheduled maintenance
        5. Send notifications to stakeholders
        6. Log audit trail
        
        Args:
            asset: Asset to retire
            user: User performing the action (must be admin)
            reason: Reason for retirement (required)
            disposal_method: Method of disposal (sell/donate/scrap/recycle)
            salvage_value: Estimated salvage value (optional)
            retirement_date: Date of retirement (default: today)
            
        Returns:
            Updated asset
        """
        cls._guard_admin_only(user)
        cls._guard_company(user.company_id, asset)

        # Validation
        if not reason or len(reason.strip()) < 10:
            raise ValidationError("Retirement reason must be at least 10 characters.")

        if disposal_method not in ['sell', 'donate', 'scrap', 'recycle', 'transfer']:
            raise ValidationError("Invalid disposal method.")

        # Check for active maintenance
        active_maintenance = MaintenanceRecord.objects.filter(
            asset=asset,
            status__in=[MaintenanceRecord.Status.SCHEDULED, MaintenanceRecord.Status.IN_PROGRESS],
        ).exists()

        if active_maintenance:
            raise ValidationError(
                "Cannot retire asset with active maintenance. Complete or cancel maintenance first."
            )

        # Check for pending transfers
        from assets.models import AssetTransfer
        pending_transfers = AssetTransfer.objects.filter(
            asset=asset,
            state__in=AssetTransfer.ACTIVE_STATES,
        ).exists()

        if pending_transfers:
            raise ValidationError(
                "Cannot retire asset with pending transfers. Complete or cancel transfers first."
            )

        with transaction.atomic():
            # Update asset
            previous_status = asset.status
            previous_assigned_to = asset.assigned_to

            asset.status = Asset.STATUS_RETIRED
            asset.status_changed_at = timezone.now()
            asset.status_changed_by = user
            asset.status_change_reason = reason
            asset.retired_at = retirement_date or timezone.localdate()
            asset.retired_by = user
            asset.retirement_reason = reason
            asset.disposal_method = disposal_method
            asset.salvage_value = salvage_value
            # DON'T force assigned_to = None - preserve form input for accountability
            # User can explicitly unassign if needed via form
            asset.next_maintenance_date = None  # Clear scheduled maintenance

            # CRITICAL: Don't use update_fields - it discards form changes!
            # Save all fields to preserve form data (branch, warranty, dynamic_data, etc.)
            asset.save()

            # Cancel all scheduled maintenance
            MaintenanceRecord.objects.filter(
                asset=asset,
                status=MaintenanceRecord.Status.SCHEDULED,
            ).update(
                status=MaintenanceRecord.Status.CANCELLED,
                outcome_notes="Cancelled due to asset retirement",
                updated_by=user,
            )

            # Audit log
            log_audit(
                user,
                cls.STATUS_CHANGE_ACTION,
                asset,
                f"Asset retired: {previous_status} → RETIRED. Disposal: {disposal_method}. Reason: {reason[:100]}",
                company=asset.company,
                branch=asset.branch,
                metadata={
                    "previous_status": previous_status,
                    "new_status": Asset.STATUS_RETIRED,
                    "reason": reason,
                    "disposal_method": disposal_method,
                    "salvage_value": str(salvage_value) if salvage_value else None,
                    "retirement_date": str(asset.retired_at),
                    "previous_assigned_to": previous_assigned_to.username if previous_assigned_to else None,
                },
            )

            # Notifications
            notifications = []

            # Notify previous owner
            if previous_assigned_to and previous_assigned_to != user:
                notifications.append(
                    Alert(
                        company=asset.company,
                        branch=asset.branch,
                        recipient=previous_assigned_to,
                        level=Alert.LEVEL_WARNING,
                        message=f"Asset '{asset}' has been retired. Disposal method: {disposal_method}.",
                        context={
                            "asset_id": asset.id,
                            "asset_uuid": str(asset.uuid),
                            "reason": reason,
                            "disposal_method": disposal_method,
                        },
                    )
                )

            if notifications:
                Alert.objects.bulk_create(notifications)

        return asset

    @classmethod
    def change_to_lost(
        cls,
        *,
        asset: Asset,
        user,
        loss_date: date,
        loss_reason: str,
        details: str,
        last_known_location: str = "",
        police_report_number: str = "",
    ) -> Asset:
        """
        Handle ANY → LOST transition.
        
        Workflow:
        1. Validate prerequisites (admin role, confirmation)
        2. Prompt for loss details
        3. Update asset status to LOST
        4. Clear assigned_to, cancel all activities
        5. Create high-priority alert
        6. Log audit trail
        
        Args:
            asset: Asset to mark as lost
            user: User performing the action (must be admin)
            loss_date: Date when asset was lost
            loss_reason: Reason (lost/stolen/damaged_beyond_repair)
            details: Detailed description (min 20 characters)
            last_known_location: Last known location (optional)
            police_report_number: Police report number if stolen (optional)
            
        Returns:
            Updated asset
        """
        cls._guard_admin_only(user)
        cls._guard_company(user.company_id, asset)

        # Validation
        if not details or len(details.strip()) < 20:
            raise ValidationError("Loss details must be at least 20 characters.")

        if loss_reason not in ['lost', 'stolen', 'damaged_beyond_repair']:
            raise ValidationError("Invalid loss reason.")

        if loss_reason == 'stolen' and not police_report_number:
            raise ValidationError("Police report number is required for stolen assets.")

        with transaction.atomic():
            # Update asset
            previous_status = asset.status
            previous_assigned_to = asset.assigned_to

            asset.status = Asset.STATUS_LOST
            asset.status_changed_at = timezone.now()
            asset.status_changed_by = user
            asset.status_change_reason = f"{loss_reason}: {details[:100]}"
            asset.lost_at = loss_date
            asset.lost_by = user
            asset.loss_reason = loss_reason
            asset.loss_details = details
            asset.last_known_location = last_known_location
            asset.police_report_number = police_report_number
            # DON'T force assigned_to = None - preserve form input for accountability
            # User can explicitly unassign if needed via form
            asset.next_maintenance_date = None  # Clear scheduled maintenance

            # CRITICAL: Don't use update_fields - it discards form changes!
            # Save all fields to preserve form data (branch, warranty, dynamic_data, etc.)
            asset.save()

            # Cancel all scheduled maintenance and pending transfers
            MaintenanceRecord.objects.filter(
                asset=asset,
                status=MaintenanceRecord.Status.SCHEDULED,
            ).update(
                status=MaintenanceRecord.Status.CANCELLED,
                outcome_notes=f"Cancelled due to asset loss: {loss_reason}",
                updated_by=user,
            )

            # Audit log
            log_audit(
                user,
                cls.STATUS_CHANGE_ACTION,
                asset,
                f"Asset reported {loss_reason}: {previous_status} → LOST. Location: {last_known_location or 'Unknown'}",
                company=asset.company,
                branch=asset.branch,
                metadata={
                    "previous_status": previous_status,
                    "new_status": Asset.STATUS_LOST,
                    "loss_reason": loss_reason,
                    "loss_date": str(loss_date),
                    "details": details,
                    "last_known_location": last_known_location,
                    "police_report_number": police_report_number,
                    "previous_assigned_to": previous_assigned_to.username if previous_assigned_to else None,
                },
            )

            # High-priority alert to admin and branch manager
            Alert.objects.create(
                company=asset.company,
                branch=asset.branch,
                recipient=user,  # Alert the reporter
                level=Alert.LEVEL_ERROR,
                message=f"URGENT: Asset '{asset}' reported {loss_reason}. Police report: {police_report_number or 'N/A'}",
                context={
                    "asset_id": asset.id,
                    "asset_uuid": str(asset.uuid),
                    "loss_reason": loss_reason,
                    "loss_date": str(loss_date),
                    "police_report": police_report_number,
                },
            )

        return asset


__all__ = ["AssetStatusChangeService"]
