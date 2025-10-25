"""Maintenance service layer providing business rules for scheduling and tracking asset maintenance."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from assets.models import Asset, MaintenanceRecord
from audit.utils import MAINTENANCE_ACTION, log_audit
from tenancy.models import Alert


@dataclass(frozen=True)
class MaintenanceNotification:
    recipient_id: int
    level: str
    message: str
    context: dict


class MaintenanceService:
    """Encapsulates maintenance workflow logic with RBAC, tenancy guards, and alerting."""

    @staticmethod
    def _guard_company(user_company_id: int, asset: Asset) -> None:
        if asset.company_id != user_company_id:
            raise PermissionDenied("You may only manage maintenance for assets in your company scope.")

    @staticmethod
    def _guard_roles(user) -> None:
        if getattr(user, "role", "user") not in {"admin", "manager"} and not user.is_superuser:
            raise PermissionDenied("Only managers or administrators may manage asset maintenance records.")

    @staticmethod
    def _validate_asset_ready(asset: Asset) -> None:
        if not asset.maintenance_enabled:
            raise ValidationError("Maintenance tracking is not enabled for this asset.")
        if asset.company_id is None:
            raise ValidationError("Asset must belong to a company before scheduling maintenance.")

    @staticmethod
    def _validate_schedule_date(scheduled_for: date) -> None:
        if scheduled_for < timezone.localdate():
            raise ValidationError("Scheduled maintenance date cannot be in the past.")

    @staticmethod
    def _build_context(record: MaintenanceRecord, extra: Optional[dict] = None) -> dict:
        context = {
            "maintenance_uuid": str(record.uuid),
            "asset_id": record.asset_id,
            "asset_uuid": str(record.asset.uuid),
            "status": record.status,
            "scheduled_for": record.scheduled_for.isoformat(),
            "company_id": record.company_id,
            "branch_id": record.branch_id,
        }
        if extra:
            context.update(extra)
        return context

    @classmethod
    def schedule(
        cls,
        *,
        asset: Asset,
        scheduled_for: date,
        created_by,
        supervisor=None,
        description: str = "",
    ) -> MaintenanceRecord:
        cls._guard_roles(created_by)
        cls._guard_company(created_by.company_id, asset)
        cls._validate_asset_ready(asset)
        cls._validate_schedule_date(scheduled_for)

        with transaction.atomic():
            record = MaintenanceRecord.objects.create(
                asset=asset,
                company=asset.company,
                branch=asset.branch,
                status=MaintenanceRecord.Status.SCHEDULED,
                scheduled_for=scheduled_for,
                supervisor=supervisor,
                description=description,
                created_by=created_by,
                updated_by=created_by,
            )

            asset.next_maintenance_date = scheduled_for
            if asset.last_maintenance_date is None:
                asset.last_maintenance_date = None
            asset.save(update_fields=["next_maintenance_date", "last_maintenance_date", "updated_at"])

            log_audit(
                created_by,
                MAINTENANCE_ACTION,
                asset,
                f"Maintenance scheduled for {scheduled_for:%Y-%m-%d}.",
                company=asset.company,
                branch=asset.branch,
            )

            cls._create_alerts(
                company_id=asset.company_id,
                branch_id=asset.branch_id,
                notifications=[
                    MaintenanceNotification(
                        recipient_id=created_by.id,
                        level=Alert.LEVEL_INFO,
                        message=f"Maintenance scheduled for asset {asset} on {scheduled_for:%Y-%m-%d}.",
                        context=cls._build_context(record),
                    )
                ],
            )
        return record

    @classmethod
    def start(cls, *, record: MaintenanceRecord, started_by) -> MaintenanceRecord:
        """
        Start scheduled maintenance and update asset status to IN_MAINTENANCE.
        
        Workflow (ServiceNow/IBM Maximo/SAP EAM best practices):
        1. MaintenanceRecord: SCHEDULED → IN_PROGRESS
        2. Asset Status: ACTIVE → IN_MAINTENANCE
        3. Log audit trail with timestamp
        4. Track who started the maintenance
        """
        cls._guard_roles(started_by)
        cls._guard_company(started_by.company_id, record.asset)
        if record.status not in {
            MaintenanceRecord.Status.SCHEDULED,
            MaintenanceRecord.Status.IN_PROGRESS,
        }:
            raise ValidationError("Only scheduled maintenance can be started.")

        with transaction.atomic():
            # Update maintenance record status
            record.status = MaintenanceRecord.Status.IN_PROGRESS
            record.started_at = timezone.now()
            record.performed_by = started_by  # Track who performed the maintenance
            record.updated_by = started_by
            record.save(update_fields=["status", "started_at", "performed_by", "updated_by", "updated_at"])

            # Update asset status to IN_MAINTENANCE (world-class workflow)
            asset = record.asset
            previous_status = asset.status
            asset.status = Asset.STATUS_IN_MAINTENANCE
            asset.save(update_fields=["status", "updated_at"])

            # Audit log with detailed context
            log_audit(
                started_by,
                MAINTENANCE_ACTION,
                asset,
                f"Maintenance started. Asset status changed: {previous_status} → IN_MAINTENANCE",
                company=record.company,
                branch=record.branch,
                metadata={
                    "maintenance_uuid": str(record.uuid),
                    "previous_status": previous_status,
                    "new_status": Asset.STATUS_IN_MAINTENANCE,
                    "started_by": started_by.username,
                },
            )

        return record

    @classmethod
    def complete(
        cls,
        *,
        record: MaintenanceRecord,
        completed_by,
        outcome_notes: str = "",
        cost: Optional[float] = None,
    ) -> MaintenanceRecord:
        """
        Complete maintenance and restore asset to ACTIVE status.
        
        Workflow (ServiceNow/IBM Maximo/SAP EAM best practices):
        1. MaintenanceRecord: IN_PROGRESS/SCHEDULED → COMPLETED
        2. Asset Status: IN_MAINTENANCE → ACTIVE
        3. Update last_maintenance_date and calculate next_maintenance_date
        4. Log audit trail with cost and outcome notes
        5. Track who completed the maintenance
        """
        cls._guard_roles(completed_by)
        cls._guard_company(completed_by.company_id, record.asset)
        if record.status not in {
            MaintenanceRecord.Status.SCHEDULED,
            MaintenanceRecord.Status.IN_PROGRESS,
        }:
            raise ValidationError("Only scheduled or in-progress maintenance can be completed.")

        with transaction.atomic():
            # Update maintenance record
            record.status = MaintenanceRecord.Status.COMPLETED
            record.completed_at = timezone.now()
            record.outcome_notes = outcome_notes
            if cost is not None:
                record.cost = cost
            if not record.performed_by:
                record.performed_by = completed_by  # Track performer if not set
            record.updated_by = completed_by
            record.save(update_fields=[
                "status",
                "completed_at",
                "outcome_notes",
                "cost",
                "performed_by",
                "updated_by",
                "updated_at",
            ])

            # Update asset: restore to ACTIVE and update maintenance dates
            asset = record.asset
            previous_status = asset.status
            asset.last_maintenance_date = timezone.localdate()
            if asset.maintenance_interval_days:
                asset.next_maintenance_date = asset.last_maintenance_date + timedelta(days=asset.maintenance_interval_days)
            else:
                asset.next_maintenance_date = None
            
            # Restore asset to ACTIVE if it was IN_MAINTENANCE (world-class workflow)
            if asset.status == Asset.STATUS_IN_MAINTENANCE:
                asset.status = Asset.STATUS_ACTIVE
            
            asset.save(update_fields=["last_maintenance_date", "next_maintenance_date", "status", "updated_at"])

            # Audit log with detailed context
            log_audit(
                completed_by,
                MAINTENANCE_ACTION,
                asset,
                f"Maintenance completed. Asset status changed: {previous_status} → {asset.status}",
                company=record.company,
                branch=record.branch,
                metadata={
                    "maintenance_uuid": str(record.uuid),
                    "cost": record.cost,
                    "previous_status": previous_status,
                    "new_status": asset.status,
                    "completed_by": completed_by.username,
                    "outcome_notes": outcome_notes[:100] if outcome_notes else None,  # First 100 chars
                },
            )

        return record

    @classmethod
    def cancel(cls, *, record: MaintenanceRecord, cancelled_by, reason: str = "") -> MaintenanceRecord:
        """
        Cancel maintenance and restore asset to ACTIVE status if needed.
        
        Workflow (ServiceNow/IBM Maximo/SAP EAM best practices):
        1. MaintenanceRecord: SCHEDULED/IN_PROGRESS → CANCELLED
        2. Asset Status: IN_MAINTENANCE → ACTIVE (if applicable)
        3. Clear next_maintenance_date if it matches scheduled date
        4. Log audit trail with cancellation reason
        """
        cls._guard_roles(cancelled_by)
        cls._guard_company(cancelled_by.company_id, record.asset)
        if record.status == MaintenanceRecord.Status.COMPLETED:
            raise ValidationError("Completed maintenance cannot be cancelled.")

        with transaction.atomic():
            # Update maintenance record
            record.status = MaintenanceRecord.Status.CANCELLED
            record.outcome_notes = reason
            record.updated_by = cancelled_by
            record.save(update_fields=["status", "outcome_notes", "updated_by", "updated_at"])

            # Update asset: restore to ACTIVE if it was IN_MAINTENANCE
            asset = record.asset
            previous_status = asset.status
            
            if asset.next_maintenance_date == record.scheduled_for:
                asset.next_maintenance_date = None
            
            # Restore asset to ACTIVE if it was IN_MAINTENANCE (world-class workflow)
            if asset.status == Asset.STATUS_IN_MAINTENANCE:
                asset.status = Asset.STATUS_ACTIVE
            
            asset.save(update_fields=["next_maintenance_date", "status", "updated_at"])

            # Audit log with detailed context
            log_audit(
                cancelled_by,
                MAINTENANCE_ACTION,
                asset,
                f"Maintenance cancelled. Asset status changed: {previous_status} → {asset.status}. Reason: {reason}",
                company=record.company,
                branch=record.branch,
                metadata={
                    "maintenance_uuid": str(record.uuid),
                    "previous_status": previous_status,
                    "new_status": asset.status,
                    "cancelled_by": cancelled_by.username,
                    "cancellation_reason": reason[:100] if reason else None,  # First 100 chars
                },
            )

        return record

    @classmethod
    def send_overdue_alerts(cls, *, company_id: int) -> None:
        overdue_records = MaintenanceRecord.objects.filter(
            company_id=company_id,
            status=MaintenanceRecord.Status.SCHEDULED,
            scheduled_for__lt=timezone.localdate(),
        ).select_related("asset")

        notifications: list[MaintenanceNotification] = []
        for record in overdue_records:
            asset = record.asset
            notifications.append(
                MaintenanceNotification(
                    recipient_id=asset.assigned_to_id or record.created_by_id,
                    level=Alert.LEVEL_WARNING,
                    message=f"Maintenance overdue for asset {asset} (scheduled {record.scheduled_for:%Y-%m-%d}).",
                    context=cls._build_context(record),
                )
            )

        if notifications:
            cls._create_alerts(company_id=company_id, branch_id=None, notifications=notifications)

    @staticmethod
    def _create_alerts(*, company_id: int, branch_id: Optional[int], notifications: Iterable[MaintenanceNotification]) -> None:
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
        if alerts:
            Alert.objects.bulk_create(alerts)


__all__ = ["MaintenanceService"]
