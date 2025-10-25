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
    context: Optional[Dict[str, Any]] = None,
) -> AssetTransfer:
    """Create a new transfer request for an asset and notify the intended recipient."""

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

    from_user = asset.assigned_to
    from_branch = asset.branch

    with transaction.atomic():
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
            f"Transfer initiated for asset to {to_user}. Comment: {initiator_comment}".strip(),
            company=asset.company,
            branch=from_branch,
            related_user=to_user,
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

        if decision == AssetTransfer.Decision.APPROVED:
            transfer.state = AssetTransfer.TransferState.AWAITING_ADMIN
            status_message = "Receiver approved the transfer. Awaiting admin review."
        else:
            transfer.state = AssetTransfer.TransferState.RECEIVER_REJECTED
            status_message = "Receiver rejected the transfer request."

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
            asset.assigned_to = transfer.to_user
            if transfer.to_branch_id:
                asset.branch_id = transfer.to_branch_id
                update_fields.append("branch")
            asset.status = Asset.STATUS_TRANSFERRED
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

            log_audit(
                reviewer,
                ASSIGN_ACTION,
                asset,
                f"Transfer completed. Asset reassigned to {transfer.to_user}.",
                company=transfer.company,
                branch=transfer.to_branch or transfer.from_branch or asset.branch,
                related_user=transfer.to_user,
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
                f"Transfer rejected by admin. Comment: {comment}",
                company=transfer.company,
                branch=transfer.from_branch or asset.branch,
                related_user=transfer.initiator,
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
