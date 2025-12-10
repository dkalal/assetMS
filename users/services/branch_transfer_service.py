# users/services/branch_transfer_service.py
"""
User Branch Transfer Service Layer

WORLD-CLASS: Complete service layer for hybrid Technique 3 + 5 + Approval workflow.

Business Logic:
1. Initiation: Admin creates transfer request, user notified to select assets
2. Selection: User chooses which assets to transfer, provides reasons
3. Approval: Admin reviews and approves/rejects selections
4. Execution: System transfers approved assets, unassigns rejected/unselected

Inspired by:
- ServiceNow ITAM: Comprehensive workflow engine
- IBM Maximo: Asset transfer service
- SAP EAM: Multi-step approval process
- Oracle EBS: Requisition-to-transfer flow

Architecture:
- Service-oriented architecture (SOA)
- Transaction-based (ACID compliance)
- Event-driven notifications
- Complete audit trail
- Performance optimized
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from assets.models import Asset
from audit.utils import log_audit
from tenancy.models import Alert, Branch, Company, UserBranch
from users.models_transfer import UserBranchTransferRequest, AssetTransferSelection


@dataclass
class TransferResult:
    """Result object for transfer operations"""
    success: bool
    message: str
    data: Dict[str, Any]
    errors: List[str] = None


class UserBranchTransferService:
    """
    WORLD-CLASS: Service layer for user branch transfer workflow.
    
    Methods:
    - initiate_transfer: Start transfer process
    - submit_asset_selections: User selects assets
    - approve_transfer: Admin approves transfer
    - reject_transfer: Admin rejects transfer
    - execute_transfer: Execute approved transfer
    - cancel_transfer: Cancel pending transfer
    
    Security:
    - Multi-tenancy enforcement
    - Role-based permissions
    - Transaction safety
    - Complete audit trail
    """
    
    # ============================================================================
    # PHASE 1: INITIATION
    # ============================================================================
    
    @classmethod
    def initiate_transfer(
        cls,
        *,
        user,
        to_branch: Branch,
        initiated_by,
        reason: str,
        effective_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransferResult:
        """
        Initiate user branch transfer workflow.
        
        Process:
        1. Validate permissions (admin/manager only)
        2. Validate company consistency
        3. Check for active transfers
        4. Create transfer request
        5. Create asset selections for all user's assets
        6. Notify user to select assets
        7. Audit log
        
        Args:
            user: User to transfer
            to_branch: Destination branch
            initiated_by: Admin/Manager initiating transfer
            reason: Reason for transfer
            effective_date: Optional effective date (ISO format)
            metadata: Optional metadata (e.g., HR ticket number)
        
        Returns:
            TransferResult with transfer_request_id
        
        Raises:
            PermissionDenied: If initiator lacks permissions
            ValidationError: If validation fails
        """
        
        try:
            with transaction.atomic():
                # 1. Validate permissions
                cls._validate_initiation_permissions(initiated_by, user, to_branch)
                
                # 2. Check for active transfers
                active_transfer = UserBranchTransferRequest.objects.filter(
                    user=user,
                    company=user.company,
                    status__in=UserBranchTransferRequest.ACTIVE_STATES
                ).first()
                
                if active_transfer:
                    raise ValidationError(
                        f"User already has an active transfer request (ID: {active_transfer.id})"
                    )
                
                # 3. Get user's current branch
                from_branch = user.primary_branch
                
                # 4. Validate branch change
                if from_branch and from_branch.id == to_branch.id:
                    raise ValidationError("User is already in the destination branch")
                
                # 5. Get user's active assets
                user_assets = Asset.objects.filter(
                    assigned_to=user,
                    company=user.company,
                    status=Asset.STATUS_ACTIVE
                ).select_related('category', 'branch')
                
                if not user_assets.exists():
                    raise ValidationError("User has no active assets to transfer")
                
                # 6. Create transfer request
                transfer_request = UserBranchTransferRequest.objects.create(
                    company=user.company,
                    user=user,
                    from_branch=from_branch,
                    to_branch=to_branch,
                    status=UserBranchTransferRequest.STATUS_PENDING_USER_SELECTION,
                    initiated_by=initiated_by,
                    initiation_reason=reason,
                    total_assets=user_assets.count(),
                    metadata=metadata or {}
                )
                
                # Add effective date to metadata if provided
                if effective_date:
                    transfer_request.metadata['effective_date'] = effective_date
                    transfer_request.save(update_fields=['metadata'])
                
                # 7. Create asset selections for all assets
                asset_selections = []
                for asset in user_assets:
                    selection = AssetTransferSelection(
                        transfer_request=transfer_request,
                        asset=asset,
                        company=user.company,
                        status=AssetTransferSelection.STATUS_NOT_SELECTED
                    )
                    selection.create_snapshot()
                    asset_selections.append(selection)
                
                AssetTransferSelection.objects.bulk_create(asset_selections)
                
                # 8. Create audit log
                log_audit(
                    user=initiated_by,
                    action='user_transfer_initiated',
                    target=user,
                    description=f"User branch transfer initiated: {from_branch.name if from_branch else 'N/A'} → {to_branch.name}",
                    company=user.company,
                    branch=to_branch,
                    metadata={
                        'transfer_request_id': transfer_request.id,
                        'from_branch_id': from_branch.id if from_branch else None,
                        'from_branch_name': from_branch.name if from_branch else None,
                        'to_branch_id': to_branch.id,
                        'to_branch_name': to_branch.name,
                        'total_assets': user_assets.count(),
                        'reason': reason,
                        'effective_date': effective_date
                    }
                )
                
                # 9. Notify user
                cls._notify_user_selection_pending(transfer_request)
                
                # 10. Notify initiator
                Alert.objects.create(
                    company=user.company,
                    branch=to_branch,
                    recipient=initiated_by,
                    level=Alert.LEVEL_SUCCESS,
                    message=f"Transfer request created for {user.get_full_name() or user.username}. Waiting for user to select assets.",
                    context={
                        'transfer_request_id': transfer_request.id,
                        'user_id': user.id,
                        'username': user.username,
                        'total_assets': user_assets.count()
                    }
                )
                
                return TransferResult(
                    success=True,
                    message=f"Transfer request created. User notified to select assets.",
                    data={
                        'transfer_request_id': transfer_request.id,
                        'user_id': user.id,
                        'username': user.username,
                        'from_branch': from_branch.name if from_branch else None,
                        'to_branch': to_branch.name,
                        'total_assets': user_assets.count(),
                        'status': transfer_request.status,
                        'initiated_at': transfer_request.initiated_at.isoformat()
                    }
                )
        
        except (PermissionDenied, ValidationError) as e:
            return TransferResult(
                success=False,
                message=str(e),
                data={},
                errors=[str(e)]
            )
        except Exception as e:
            return TransferResult(
                success=False,
                message="Transfer initiation failed",
                data={},
                errors=[str(e)]
            )
    
    # ============================================================================
    # PHASE 2: USER ASSET SELECTION
    # ============================================================================
    
    @classmethod
    def submit_asset_selections(
        cls,
        *,
        transfer_request: UserBranchTransferRequest,
        selected_asset_ids: List[int],
        selection_reasons: Dict[int, str],
        notes: str = ""
    ) -> TransferResult:
        """
        User submits their asset selections.
        
        Process:
        1. Validate transfer request state
        2. Validate user permissions
        3. Update asset selections
        4. Update transfer request status
        5. Notify admin/manager for approval
        6. Audit log
        
        Args:
            transfer_request: Transfer request object
            selected_asset_ids: List of asset IDs user wants to transfer
            selection_reasons: Dict mapping asset_id → reason
            notes: Optional overall notes from user
        
        Returns:
            TransferResult with selection summary
        """
        
        try:
            with transaction.atomic():
                # 1. Validate state
                if not transfer_request.can_user_select_assets:
                    raise ValidationError(
                        f"Cannot select assets. Transfer is in {transfer_request.get_status_display()} state."
                    )
                
                # 2. Get all selections
                all_selections = transfer_request.asset_selections.select_related('asset').all()
                
                selected_count = 0
                not_selected_count = 0
                
                # 3. Update selections
                for selection in all_selections:
                    is_selected = selection.asset_id in selected_asset_ids
                    
                    selection.selected_by_user = is_selected
                    selection.user_selected_at = timezone.now()
                    
                    if is_selected:
                        selection.status = AssetTransferSelection.STATUS_SELECTED
                        selection.user_selection_reason = selection_reasons.get(
                            selection.asset_id, ""
                        )
                        selected_count += 1
                    else:
                        selection.status = AssetTransferSelection.STATUS_NOT_SELECTED
                        not_selected_count += 1
                    
                    selection.save(update_fields=[
                        'selected_by_user',
                        'user_selected_at',
                        'user_selection_reason',
                        'status'
                    ])
                
                # 4. Update transfer request
                transfer_request.status = UserBranchTransferRequest.STATUS_PENDING_APPROVAL
                transfer_request.user_selection_at = timezone.now()
                transfer_request.user_selection_notes = notes
                transfer_request.assets_selected_by_user = selected_count
                transfer_request.save(update_fields=[
                    'status',
                    'user_selection_at',
                    'user_selection_notes',
                    'assets_selected_by_user'
                ])
                
                # 5. Create audit log
                log_audit(
                    user=transfer_request.user,
                    action='user_transfer_selections_submitted',
                    target=transfer_request.user,
                    description=f"User submitted asset selections: {selected_count} to transfer, {not_selected_count} to return",
                    company=transfer_request.company,
                    branch=transfer_request.to_branch,
                    metadata={
                        'transfer_request_id': transfer_request.id,
                        'selected_count': selected_count,
                        'not_selected_count': not_selected_count,
                        'selected_asset_ids': selected_asset_ids,
                        'notes': notes
                    }
                )
                
                # 6. Notify admin/manager for approval
                cls._notify_approval_pending(transfer_request)
                
                # 7. Notify user (confirmation)
                Alert.objects.create(
                    company=transfer_request.company,
                    branch=transfer_request.to_branch,
                    recipient=transfer_request.user,
                    level=Alert.LEVEL_INFO,
                    message=f"Asset selections submitted. Waiting for admin approval. ({selected_count} to transfer, {not_selected_count} to return)",
                    context={
                        'transfer_request_id': transfer_request.id,
                        'selected_count': selected_count,
                        'not_selected_count': not_selected_count
                    }
                )
                
                return TransferResult(
                    success=True,
                    message=f"Selections submitted. Pending approval.",
                    data={
                        'transfer_request_id': transfer_request.id,
                        'selected_count': selected_count,
                        'not_selected_count': not_selected_count,
                        'status': transfer_request.status
                    }
                )
        
        except (ValidationError, Exception) as e:
            return TransferResult(
                success=False,
                message=str(e),
                data={},
                errors=[str(e)]
            )
    
    # ============================================================================
    # PHASE 3: ADMIN APPROVAL
    # ============================================================================
    
    @classmethod
    def approve_transfer(
        cls,
        *,
        transfer_request: UserBranchTransferRequest,
        approved_by,
        approval_reason: str = "",
        approved_asset_ids: Optional[List[int]] = None,
        auto_execute: bool = True
    ) -> TransferResult:
        """
        Admin/Manager approves transfer request.
        
        Process:
        1. Validate permissions
        2. Validate transfer state
        3. Update approval status
        4. Optionally approve selective assets
        5. Execute transfer if auto_execute=True
        6. Notify user
        7. Audit log
        
        Args:
            transfer_request: Transfer request object
            approved_by: Admin/Manager approving
            approval_reason: Reason for approval
            approved_asset_ids: Optional list of specific asset IDs to approve (None = all)
            auto_execute: Whether to execute transfer immediately
        
        Returns:
            TransferResult with approval summary
        """
        
        try:
            with transaction.atomic():
                # 1. Validate permissions
                cls._validate_approval_permissions(approved_by, transfer_request)
                
                # 2. Validate state
                if not transfer_request.can_be_approved:
                    raise ValidationError(
                        f"Cannot approve. Transfer is in {transfer_request.get_status_display()} state."
                    )
                
                # 3. Get selected assets
                selected_assets = transfer_request.get_selected_assets()
                
                if not selected_assets.exists():
                    raise ValidationError("No assets selected by user to approve")
                
                # 4. Update approval status
                approved_count = 0
                rejected_count = 0
                
                for selection in selected_assets:
                    # If selective approval specified
                    if approved_asset_ids is not None:
                        is_approved = selection.asset_id in approved_asset_ids
                    else:
                        # Approve all selected
                        is_approved = True
                    
                    selection.approved_by_admin = is_approved
                    selection.admin_decision_at = timezone.now()
                    selection.admin_decision_reason = approval_reason
                    
                    if is_approved:
                        selection.status = AssetTransferSelection.STATUS_APPROVED
                        approved_count += 1
                    else:
                        selection.status = AssetTransferSelection.STATUS_REJECTED
                        rejected_count += 1
                    
                    selection.save(update_fields=[
                        'approved_by_admin',
                        'admin_decision_at',
                        'admin_decision_reason',
                        'status'
                    ])
                
                # 5. Update transfer request
                transfer_request.status = UserBranchTransferRequest.STATUS_APPROVED
                transfer_request.approved_by = approved_by
                transfer_request.approval_decision_at = timezone.now()
                transfer_request.approval_reason = approval_reason
                transfer_request.assets_approved = approved_count
                transfer_request.save(update_fields=[
                    'status',
                    'approved_by',
                    'approval_decision_at',
                    'approval_reason',
                    'assets_approved'
                ])
                
                # 6. Create audit log
                log_audit(
                    user=approved_by,
                    action='user_transfer_approved',
                    target=transfer_request.user,
                    description=f"User branch transfer approved: {approved_count} assets to transfer, {rejected_count} rejected",
                    company=transfer_request.company,
                    branch=transfer_request.to_branch,
                    metadata={
                        'transfer_request_id': transfer_request.id,
                        'approved_count': approved_count,
                        'rejected_count': rejected_count,
                        'approval_reason': approval_reason
                    }
                )
                
                # 7. Execute if requested
                execution_result = None
                if auto_execute:
                    execution_result = cls.execute_transfer(
                        transfer_request=transfer_request,
                        executed_by=approved_by
                    )
                    
                    if not execution_result.success:
                        raise ValidationError(f"Execution failed: {execution_result.message}")
                
                # 8. Notify user
                Alert.objects.create(
                    company=transfer_request.company,
                    branch=transfer_request.to_branch,
                    recipient=transfer_request.user,
                    level=Alert.LEVEL_SUCCESS,
                    message=f"Branch transfer approved! {approved_count} assets will be transferred to {transfer_request.to_branch.name}.",
                    context={
                        'transfer_request_id': transfer_request.id,
                        'approved_count': approved_count,
                        'rejected_count': rejected_count,
                        'to_branch': transfer_request.to_branch.name
                    }
                )
                
                return TransferResult(
                    success=True,
                    message=f"Transfer approved. {approved_count} assets approved.",
                    data={
                        'transfer_request_id': transfer_request.id,
                        'approved_count': approved_count,
                        'rejected_count': rejected_count,
                        'status': transfer_request.status,
                        'execution_result': execution_result.data if execution_result else None
                    }
                )
        
        except (PermissionDenied, ValidationError, Exception) as e:
            return TransferResult(
                success=False,
                message=str(e),
                data={},
                errors=[str(e)]
            )
    
    @classmethod
    def reject_transfer(
        cls,
        *,
        transfer_request: UserBranchTransferRequest,
        rejected_by,
        rejection_reason: str
    ) -> TransferResult:
        """
        Admin/Manager rejects transfer request.
        
        Process:
        1. Validate permissions
        2. Update rejection status
        3. Notify user
        4. Audit log
        
        No assets are transferred, user stays in original branch.
        """
        
        try:
            with transaction.atomic():
                # 1. Validate permissions
                cls._validate_approval_permissions(rejected_by, transfer_request)
                
                # 2. Validate state
                if not transfer_request.can_be_approved:
                    raise ValidationError(
                        f"Cannot reject. Transfer is in {transfer_request.get_status_display()} state."
                    )
                
                # 3. Update transfer request
                transfer_request.status = UserBranchTransferRequest.STATUS_REJECTED
                transfer_request.approved_by = rejected_by
                transfer_request.approval_decision_at = timezone.now()
                transfer_request.rejection_reason = rejection_reason
                transfer_request.save(update_fields=[
                    'status',
                    'approved_by',
                    'approval_decision_at',
                    'rejection_reason'
                ])
                
                # 4. Create audit log
                log_audit(
                    user=rejected_by,
                    action='user_transfer_rejected',
                    target=transfer_request.user,
                    description=f"User branch transfer rejected: {rejection_reason}",
                    company=transfer_request.company,
                    branch=transfer_request.from_branch or transfer_request.to_branch,
                    metadata={
                        'transfer_request_id': transfer_request.id,
                        'rejection_reason': rejection_reason
                    }
                )
                
                # 5. Notify user
                Alert.objects.create(
                    company=transfer_request.company,
                    branch=transfer_request.from_branch or transfer_request.to_branch,
                    recipient=transfer_request.user,
                    level=Alert.LEVEL_WARNING,
                    message=f"Branch transfer request rejected. Reason: {rejection_reason}",
                    context={
                        'transfer_request_id': transfer_request.id,
                        'rejection_reason': rejection_reason
                    }
                )
                
                # 6. Notify initiator
                if transfer_request.initiated_by:
                    Alert.objects.create(
                        company=transfer_request.company,
                        branch=transfer_request.from_branch or transfer_request.to_branch,
                        recipient=transfer_request.initiated_by,
                        level=Alert.LEVEL_WARNING,
                        message=f"Transfer request for {transfer_request.user.username} rejected by {rejected_by.username}",
                        context={
                            'transfer_request_id': transfer_request.id,
                            'rejection_reason': rejection_reason
                        }
                    )
                
                return TransferResult(
                    success=True,
                    message="Transfer rejected successfully",
                    data={
                        'transfer_request_id': transfer_request.id,
                        'status': transfer_request.status,
                        'rejection_reason': rejection_reason
                    }
                )
        
        except (PermissionDenied, ValidationError, Exception) as e:
            return TransferResult(
                success=False,
                message=str(e),
                data={},
                errors=[str(e)]
            )
    
    # ============================================================================
    # PHASE 4: EXECUTION
    # ============================================================================
    
    @classmethod
    def execute_transfer(
        cls,
        *,
        transfer_request: UserBranchTransferRequest,
        executed_by
    ) -> TransferResult:
        """
        Execute approved transfer: Transfer assets and update user branch.
        
        Process:
        1. Update user's primary branch
        2. Transfer approved assets to new branch
        3. Unassign rejected and not-selected assets
        4. Update transfer request status
        5. Notifications
        6. Complete audit trail
        
        WORLD-CLASS: This is the core execution engine.
        """
        
        try:
            with transaction.atomic():
                # 1. Validate state
                if not transfer_request.can_be_executed:
                    raise ValidationError(
                        f"Cannot execute. Transfer is in {transfer_request.get_status_display()} state."
                    )
                
                # 2. Update user's primary branch
                UserBranch.ensure_primary(
                    user=transfer_request.user,
                    company=transfer_request.company,
                    branch=transfer_request.to_branch
                )
                
                transferred_count = 0
                unassigned_count = 0
                errors = []
                
                # 3. Transfer approved assets
                approved_selections = transfer_request.get_approved_assets()
                
                for selection in approved_selections:
                    try:
                        asset = selection.asset
                        old_branch = asset.branch
                        
                        # Update asset branch
                        asset.branch = transfer_request.to_branch
                        asset.save(update_fields=['branch', 'updated_at'])
                        
                        # Update selection status
                        selection.status = AssetTransferSelection.STATUS_TRANSFERRED
                        selection.executed_at = timezone.now()
                        selection.save(update_fields=['status', 'executed_at'])
                        
                        # Audit log per asset
                        log_audit(
                            user=executed_by,
                            action='asset_transferred_user_branch_change',
                            target=asset,
                            description=f"Asset transferred from {old_branch.name if old_branch else 'N/A'} to {transfer_request.to_branch.name} (user transfer)",
                            company=transfer_request.company,
                            branch=transfer_request.to_branch,
                            metadata={
                                'transfer_request_id': transfer_request.id,
                                'old_branch_id': old_branch.id if old_branch else None,
                                'old_branch_name': old_branch.name if old_branch else None,
                                'new_branch_id': transfer_request.to_branch.id,
                                'new_branch_name': transfer_request.to_branch.name,
                                'user_id': transfer_request.user.id,
                                'username': transfer_request.user.username
                            }
                        )
                        
                        transferred_count += 1
                        
                    except Exception as e:
                        selection.execution_error = str(e)
                        selection.save(update_fields=['execution_error'])
                        errors.append(f"Asset {asset.name}: {str(e)}")
                
                # 4. Unassign not-selected and rejected assets
                to_unassign = transfer_request.asset_selections.filter(
                    status__in=[
                        AssetTransferSelection.STATUS_NOT_SELECTED,
                        AssetTransferSelection.STATUS_REJECTED
                    ]
                )
                
                for selection in to_unassign:
                    try:
                        asset = selection.asset
                        
                        # Unassign asset
                        asset.assigned_to = None
                        asset.save(update_fields=['assigned_to', 'updated_at'])
                        
                        # Update selection status
                        selection.status = AssetTransferSelection.STATUS_UNASSIGNED
                        selection.executed_at = timezone.now()
                        selection.save(update_fields=['status', 'executed_at'])
                        
                        # Audit log per asset
                        log_audit(
                            user=executed_by,
                            action='asset_unassigned_user_branch_change',
                            target=asset,
                            description=f"Asset unassigned from {transfer_request.user.username} (user transfer to {transfer_request.to_branch.name})",
                            company=transfer_request.company,
                            branch=asset.branch,
                            metadata={
                                'transfer_request_id': transfer_request.id,
                                'previous_user_id': transfer_request.user.id,
                                'previous_username': transfer_request.user.username,
                                'reason': 'not_selected_for_transfer' if selection.status == AssetTransferSelection.STATUS_NOT_SELECTED else 'admin_rejected'
                            }
                        )
                        
                        unassigned_count += 1
                        
                    except Exception as e:
                        selection.execution_error = str(e)
                        selection.save(update_fields=['execution_error'])
                        errors.append(f"Asset {asset.name}: {str(e)}")
                
                # 5. Update transfer request
                transfer_request.status = UserBranchTransferRequest.STATUS_COMPLETED
                transfer_request.completed_at = timezone.now()
                transfer_request.assets_transferred = transferred_count
                transfer_request.assets_unassigned = unassigned_count
                transfer_request.save(update_fields=[
                    'status',
                    'completed_at',
                    'assets_transferred',
                    'assets_unassigned'
                ])
                
                # 6. Create completion audit log
                log_audit(
                    user=executed_by,
                    action='user_transfer_completed',
                    target=transfer_request.user,
                    description=f"User branch transfer completed: {transferred_count} assets transferred, {unassigned_count} assets unassigned",
                    company=transfer_request.company,
                    branch=transfer_request.to_branch,
                    metadata={
                        'transfer_request_id': transfer_request.id,
                        'from_branch_id': transfer_request.from_branch.id if transfer_request.from_branch else None,
                        'from_branch_name': transfer_request.from_branch.name if transfer_request.from_branch else None,
                        'to_branch_id': transfer_request.to_branch.id,
                        'to_branch_name': transfer_request.to_branch.name,
                        'transferred_count': transferred_count,
                        'unassigned_count': unassigned_count,
                        'errors': errors if errors else None
                    }
                )
                
                # 7. Notify user (completion)
                Alert.objects.create(
                    company=transfer_request.company,
                    branch=transfer_request.to_branch,
                    recipient=transfer_request.user,
                    level=Alert.LEVEL_SUCCESS,
                    message=f"Welcome to {transfer_request.to_branch.name}! {transferred_count} assets transferred, {unassigned_count} assets returned.",
                    context={
                        'transfer_request_id': transfer_request.id,
                        'transferred_count': transferred_count,
                        'unassigned_count': unassigned_count,
                        'to_branch': transfer_request.to_branch.name
                    }
                )
                
                # 8. Notify old branch manager (if exists)
                if transfer_request.from_branch and transfer_request.from_branch.manager:
                    Alert.objects.create(
                        company=transfer_request.company,
                        branch=transfer_request.from_branch,
                        recipient=transfer_request.from_branch.manager,
                        level=Alert.LEVEL_INFO,
                        message=f"{transfer_request.user.username} transferred to {transfer_request.to_branch.name}. {unassigned_count} assets returned for reassignment.",
                        context={
                            'transfer_request_id': transfer_request.id,
                            'unassigned_count': unassigned_count
                        }
                    )
                
                # 9. Notify new branch manager
                if transfer_request.to_branch.manager and transfer_request.to_branch.manager != transfer_request.user:
                    Alert.objects.create(
                        company=transfer_request.company,
                        branch=transfer_request.to_branch,
                        recipient=transfer_request.to_branch.manager,
                        level=Alert.LEVEL_SUCCESS,
                        message=f"{transfer_request.user.username} joined your branch with {transferred_count} assets.",
                        context={
                            'transfer_request_id': transfer_request.id,
                            'transferred_count': transferred_count,
                            'user_id': transfer_request.user.id
                        }
                    )
                
                return TransferResult(
                    success=True,
                    message=f"Transfer completed successfully. {transferred_count} assets transferred, {unassigned_count} unassigned.",
                    data={
                        'transfer_request_id': transfer_request.id,
                        'transferred_count': transferred_count,
                        'unassigned_count': unassigned_count,
                        'errors': errors if errors else None,
                        'completed_at': transfer_request.completed_at.isoformat()
                    }
                )
        
        except (ValidationError, Exception) as e:
            return TransferResult(
                success=False,
                message=str(e),
                data={},
                errors=[str(e)]
            )
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    @classmethod
    def cancel_transfer(
        cls,
        *,
        transfer_request: UserBranchTransferRequest,
        cancelled_by,
        cancellation_reason: str
    ) -> TransferResult:
        """Cancel pending transfer request"""
        
        try:
            with transaction.atomic():
                if transfer_request.is_final:
                    raise ValidationError("Cannot cancel completed/rejected transfer")
                
                transfer_request.status = UserBranchTransferRequest.STATUS_CANCELLED
                transfer_request.metadata['cancelled_by'] = cancelled_by.username
                transfer_request.metadata['cancellation_reason'] = cancellation_reason
                transfer_request.metadata['cancelled_at'] = timezone.now().isoformat()
                transfer_request.save(update_fields=['status', 'metadata'])
                
                # Audit log
                log_audit(
                    user=cancelled_by,
                    action='user_transfer_cancelled',
                    target=transfer_request.user,
                    description=f"User branch transfer cancelled: {cancellation_reason}",
                    company=transfer_request.company,
                    branch=transfer_request.from_branch or transfer_request.to_branch,
                    metadata={
                        'transfer_request_id': transfer_request.id,
                        'cancellation_reason': cancellation_reason
                    }
                )
                
                # Notify user
                Alert.objects.create(
                    company=transfer_request.company,
                    branch=transfer_request.from_branch or transfer_request.to_branch,
                    recipient=transfer_request.user,
                    level=Alert.LEVEL_WARNING,
                    message=f"Branch transfer cancelled: {cancellation_reason}",
                    context={'transfer_request_id': transfer_request.id}
                )
                
                return TransferResult(
                    success=True,
                    message="Transfer cancelled successfully",
                    data={'transfer_request_id': transfer_request.id}
                )
        
        except Exception as e:
            return TransferResult(
                success=False,
                message=str(e),
                data={},
                errors=[str(e)]
            )
    
    # ============================================================================
    # USER SELF-SERVICE: INITIATION & MANAGER APPROVAL
    # ============================================================================
    
    @classmethod
    def user_initiate_transfer(
        cls,
        *,
        user,
        to_branch: Branch,
        reason: str,
        effective_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransferResult:
        """
        User initiates their own branch transfer request.
        
        WORLD-CLASS: Self-service workflow matching ServiceNow ITAM, IBM Maximo.
        
        Process:
        1. Validate user can request transfer
        2. Check for active transfers
        3. Determine if manager approval required (via policy)
        4. Create transfer request
        5. Create asset selections
        6. Notify manager (if approval required) or user (if direct to selection)
        7. Audit log
        
        Args:
            user: User requesting transfer for themselves
            to_branch: Destination branch
            reason: Reason for transfer
            effective_date: Optional effective date (ISO format)
            metadata: Optional metadata
        
        Returns:
            TransferResult with transfer_request_id
        """
        
        try:
            with transaction.atomic():
                # 1. Validate user can request transfer
                if user.company != to_branch.company:
                    raise ValidationError("Cannot transfer to branch in different company")
                
                # 2. Check for active transfers
                active_transfer = UserBranchTransferRequest.objects.filter(
                    user=user,
                    company=user.company,
                    status__in=UserBranchTransferRequest.ACTIVE_STATES
                ).first()
                
                if active_transfer:
                    raise ValidationError(
                        f"You already have an active transfer request (ID: {active_transfer.id})"
                    )
                
                # 3. Get user's current branch
                from_branch = user.primary_branch
                
                # 4. Validate branch change
                if from_branch and from_branch.id == to_branch.id:
                    raise ValidationError("You are already in the destination branch")
                
                # 5. Determine initial status (check if manager approval required)
                # For now, always require manager approval for user-initiated transfers
                # TODO: Make this configurable via MultiTenancyPolicy
                initial_status = UserBranchTransferRequest.STATUS_PENDING_MANAGER_APPROVAL
                
                # 6. Get user's active assets
                user_assets = Asset.objects.filter(
                    assigned_to=user,
                    company=user.company,
                    status=Asset.STATUS_ACTIVE
                ).select_related('category', 'branch')
                
                # 7. Create transfer request
                transfer_request = UserBranchTransferRequest.objects.create(
                    company=user.company,
                    user=user,
                    from_branch=from_branch,
                    to_branch=to_branch,
                    status=initial_status,
                    initiated_by=user,  # User initiates for themselves
                    initiation_type=UserBranchTransferRequest.INITIATION_TYPE_USER,
                    initiation_reason=reason,
                    total_assets=user_assets.count(),
                    metadata=metadata or {}
                )
                
                # Add effective date to metadata if provided
                if effective_date:
                    transfer_request.metadata['effective_date'] = effective_date
                    transfer_request.save(update_fields=['metadata'])
                
                # 8. Create asset selections for all assets
                asset_selections = []
                for asset in user_assets:
                    selection = AssetTransferSelection(
                        transfer_request=transfer_request,
                        asset=asset,
                        company=user.company,
                        status=AssetTransferSelection.STATUS_NOT_SELECTED
                    )
                    selection.create_snapshot()
                    asset_selections.append(selection)
                
                if asset_selections:
                    AssetTransferSelection.objects.bulk_create(asset_selections)
                
                # 9. Create audit log
                log_audit(
                    user=user,
                    action='user_transfer_self_initiated',
                    target=user,
                    description=f"User initiated own branch transfer: {from_branch.name if from_branch else 'N/A'} → {to_branch.name}",
                    company=user.company,
                    branch=to_branch,
                    metadata={
                        'transfer_request_id': transfer_request.id,
                        'from_branch_id': from_branch.id if from_branch else None,
                        'from_branch_name': from_branch.name if from_branch else None,
                        'to_branch_id': to_branch.id,
                        'to_branch_name': to_branch.name,
                        'total_assets': user_assets.count(),
                        'reason': reason,
                        'effective_date': effective_date,
                        'initiation_type': 'user_initiated'
                    }
                )
                
                # 10. Notify manager for approval
                cls._notify_manager_approval_pending(transfer_request)
                
                return TransferResult(
                    success=True,
                    message=f"Transfer request submitted successfully. Waiting for manager approval.",
                    data={
                        'transfer_request_id': transfer_request.id,
                        'user_id': user.id,
                        'username': user.username,
                        'from_branch': from_branch.name if from_branch else None,
                        'to_branch': to_branch.name,
                        'total_assets': user_assets.count(),
                        'status': transfer_request.status,
                        'initiated_at': transfer_request.initiated_at.isoformat()
                    }
                )
        
        except (ValidationError, Exception) as e:
            return TransferResult(
                success=False,
                message=str(e),
                data={},
                errors=[str(e)]
            )
    
    @classmethod
    def manager_approve_transfer(
        cls,
        *,
        transfer_request: UserBranchTransferRequest,
        manager,
        approval_reason: str = ""
    ) -> TransferResult:
        """
        Manager approves user-initiated transfer request.
        Moves to user asset selection stage.
        
        Process:
        1. Validate manager permissions
        2. Validate transfer state
        3. Update manager approval
        4. Move to user selection stage
        5. Notify user to select assets
        6. Audit log
        """
        
        try:
            with transaction.atomic():
                # 1. Validate state
                if transfer_request.status != UserBranchTransferRequest.STATUS_PENDING_MANAGER_APPROVAL:
                    raise ValidationError(
                        f"Transfer is not pending manager approval. Current status: {transfer_request.get_status_display()}"
                    )
                
                # 2. Validate permissions
                if transfer_request.company != manager.company:
                    raise PermissionDenied("Manager must be in same company")
                
                if manager.role not in ['admin', 'manager']:
                    raise PermissionDenied("Only managers and admins can approve transfers")
                
                # 3. Update transfer request
                transfer_request.status = UserBranchTransferRequest.STATUS_PENDING_USER_SELECTION
                transfer_request.manager_approved_by = manager
                transfer_request.manager_approval_at = timezone.now()
                transfer_request.manager_approval_reason = approval_reason
                transfer_request.save(update_fields=[
                    'status',
                    'manager_approved_by',
                    'manager_approval_at',
                    'manager_approval_reason'
                ])
                
                # 4. Create audit log
                log_audit(
                    user=manager,
                    action='user_transfer_manager_approved',
                    target=transfer_request.user,
                    description=f"Manager approved user transfer request: {transfer_request.user.username} → {transfer_request.to_branch.name}",
                    company=transfer_request.company,
                    branch=transfer_request.to_branch,
                    metadata={
                        'transfer_request_id': transfer_request.id,
                        'approval_reason': approval_reason,
                        'user_id': transfer_request.user.id,
                        'username': transfer_request.user.username
                    }
                )
                
                # 5. Notify user to select assets
                cls._notify_user_selection_pending(transfer_request)
                
                # 6. Notify manager (confirmation)
                Alert.objects.create(
                    company=transfer_request.company,
                    branch=transfer_request.to_branch,
                    recipient=manager,
                    level=Alert.LEVEL_SUCCESS,
                    message=f"Transfer request approved for {transfer_request.user.get_full_name() or transfer_request.user.username}. User will now select assets.",
                    context={
                        'transfer_request_id': transfer_request.id,
                        'user_id': transfer_request.user.id,
                        'username': transfer_request.user.username
                    }
                )
                
                return TransferResult(
                    success=True,
                    message="Transfer request approved. User notified to select assets.",
                    data={
                        'transfer_request_id': transfer_request.id,
                        'status': transfer_request.status,
                        'user_id': transfer_request.user.id,
                        'username': transfer_request.user.username
                    }
                )
        
        except (PermissionDenied, ValidationError, Exception) as e:
            return TransferResult(
                success=False,
                message=str(e),
                data={},
                errors=[str(e)]
            )
    
    @classmethod
    def manager_reject_transfer(
        cls,
        *,
        transfer_request: UserBranchTransferRequest,
        manager,
        rejection_reason: str
    ) -> TransferResult:
        """
        Manager rejects user-initiated transfer request.
        Transfer is cancelled, user stays in current branch.
        """
        
        try:
            with transaction.atomic():
                # 1. Validate state
                if transfer_request.status != UserBranchTransferRequest.STATUS_PENDING_MANAGER_APPROVAL:
                    raise ValidationError(
                        f"Transfer is not pending manager approval. Current status: {transfer_request.get_status_display()}"
                    )
                
                # 2. Validate permissions
                if transfer_request.company != manager.company:
                    raise PermissionDenied("Manager must be in same company")
                
                if manager.role not in ['admin', 'manager']:
                    raise PermissionDenied("Only managers and admins can reject transfers")
                
                # 3. Update transfer request
                transfer_request.status = UserBranchTransferRequest.STATUS_REJECTED
                transfer_request.manager_approved_by = manager
                transfer_request.manager_approval_at = timezone.now()
                transfer_request.manager_approval_reason = rejection_reason
                transfer_request.rejection_reason = rejection_reason
                transfer_request.save(update_fields=[
                    'status',
                    'manager_approved_by',
                    'manager_approval_at',
                    'manager_approval_reason',
                    'rejection_reason'
                ])
                
                # 4. Create audit log
                log_audit(
                    user=manager,
                    action='user_transfer_manager_rejected',
                    target=transfer_request.user,
                    description=f"Manager rejected user transfer request: {rejection_reason}",
                    company=transfer_request.company,
                    branch=transfer_request.from_branch or transfer_request.to_branch,
                    metadata={
                        'transfer_request_id': transfer_request.id,
                        'rejection_reason': rejection_reason,
                        'user_id': transfer_request.user.id,
                        'username': transfer_request.user.username
                    }
                )
                
                # 5. Notify user
                Alert.objects.create(
                    company=transfer_request.company,
                    branch=transfer_request.from_branch or transfer_request.to_branch,
                    recipient=transfer_request.user,
                    level=Alert.LEVEL_WARNING,
                    message=f"Your transfer request to {transfer_request.to_branch.name} was not approved. Reason: {rejection_reason}",
                    context={
                        'transfer_request_id': transfer_request.id,
                        'rejection_reason': rejection_reason
                    }
                )
                
                return TransferResult(
                    success=True,
                    message="Transfer request rejected successfully",
                    data={
                        'transfer_request_id': transfer_request.id,
                        'status': transfer_request.status,
                        'rejection_reason': rejection_reason
                    }
                )
        
        except (PermissionDenied, ValidationError, Exception) as e:
            return TransferResult(
                success=False,
                message=str(e),
                data={},
                errors=[str(e)]
            )

    @classmethod
    def _validate_initiation_permissions(cls, initiated_by, user, to_branch):
        """Validate permissions for admin-initiated transfer."""

        # Must be admin or manager (is_staff covers both in this system)
        if not (initiated_by.is_staff or initiated_by.is_superuser):
            raise PermissionDenied("Only admins and managers can initiate transfers")

        # Must be same company as user
        if initiated_by.company_id != user.company_id:
            raise PermissionDenied("Cannot transfer users from a different company")

        # Destination branch must also be in same company
        if initiated_by.company_id != to_branch.company_id:
            raise PermissionDenied("Destination branch must be in the same company")

    @classmethod
    def _validate_approval_permissions(cls, approver, transfer_request):
        """Validate permissions for approving admin-initiated transfer."""

        role = getattr(approver, 'role', '') or ''

        # Must be admin or manager (or superuser/staff)
        if role not in {"admin", "manager"} and not (approver.is_staff or approver.is_superuser):
            raise PermissionDenied("Only admins and managers can approve transfers")

        # Must be same company
        if approver.company_id != transfer_request.company_id:
            raise PermissionDenied("Cannot approve transfers from a different company")

        # Managers can only approve for their own branches
        if role.lower() == 'manager' and not approver.is_superuser:
            approver_branches = approver.user_branches.values_list('branch_id', flat=True)
            if transfer_request.to_branch_id not in approver_branches:
                raise PermissionDenied("Managers can only approve transfers to their branches")

    @classmethod
    def _notify_user_selection_pending(cls, transfer_request):
        """Notify user to select assets for their transfer request."""

        Alert.objects.create(
            company=transfer_request.company,
            branch=transfer_request.from_branch or transfer_request.to_branch,
            recipient=transfer_request.user,
            level=Alert.LEVEL_WARNING,
            message=(
                f"Branch transfer to {transfer_request.to_branch.name}: "
                f"Please select which assets to transfer with you "
                f"({transfer_request.total_assets} assets available)"
            ),
            context={
                'transfer_request_id': transfer_request.id,
                'to_branch': transfer_request.to_branch.name,
                'total_assets': transfer_request.total_assets,
                'action_required': True,
                'action_url': f'/users/transfer/{transfer_request.id}/select-assets/',
            },
        )

    @classmethod
    def _notify_manager_approval_pending(cls, transfer_request):
        """Notify branch manager (and admins) for user-initiated transfer approval."""

        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Notify branch manager at from_branch, if any
        if transfer_request.from_branch:
            branch_manager = transfer_request.from_branch.manager
            if branch_manager:
                Alert.objects.create(
                    company=transfer_request.company,
                    branch=transfer_request.from_branch,
                    recipient=branch_manager,
                    level=Alert.LEVEL_WARNING,
                    message=(
                        f"Transfer Request: {transfer_request.user.get_full_name() or transfer_request.user.username} "
                        f"wants to transfer to {transfer_request.to_branch.name}"
                    ),
                    context={
                        'transfer_request_id': transfer_request.id,
                        'user_id': transfer_request.user.id,
                        'username': transfer_request.user.username,
                        'to_branch': transfer_request.to_branch.name,
                        'total_assets': transfer_request.total_assets,
                        'action_required': True,
                        'action_url': f'/users/transfer/{transfer_request.id}/manager-review/',
                    },
                )

        # Also notify all active company admins
        admins = User.objects.filter(
            company=transfer_request.company,
            role='admin',
            is_active=True,
        )

        for admin in admins:
            Alert.objects.create(
                company=transfer_request.company,
                branch=transfer_request.to_branch,
                recipient=admin,
                level=Alert.LEVEL_INFO,
                message=(
                    f"User Transfer Request: {transfer_request.user.username} → "
                    f"{transfer_request.to_branch.name} (pending manager approval)"
                ),
                context={
                    'transfer_request_id': transfer_request.id,
                    'user_id': transfer_request.user.id,
                    'username': transfer_request.user.username,
                    'action_url': f'/users/transfer/{transfer_request.id}/manager-review/',
                },
            )

    @classmethod
    def _notify_approval_pending(cls, transfer_request):
        """Notify admins that a transfer is pending final approval."""

        from django.contrib.auth import get_user_model

        User = get_user_model()

        admins = User.objects.filter(
            company=transfer_request.company,
            is_staff=True,
        )

        for admin in admins:
            Alert.objects.create(
                company=transfer_request.company,
                branch=transfer_request.to_branch,
                recipient=admin,
                level=Alert.LEVEL_WARNING,
                message=(
                    f"Approval needed: {transfer_request.user.username} → "
                    f"{transfer_request.to_branch.name} ({transfer_request.assets_selected_by_user} assets selected)"
                ),
                context={
                    'transfer_request_id': transfer_request.id,
                    'user_id': transfer_request.user.id,
                    'username': transfer_request.user.username,
                    'selected_count': transfer_request.assets_selected_by_user,
                    'action_required': True,
                    'action_url': f'/users/transfer/{transfer_request.id}/approve/',
                },
            )
