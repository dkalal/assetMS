"""
WORLD-CLASS: Self-Service User Retirement Service

Inspired by:
- ServiceNow ITSM: Employee separation requests with multi-level approvals
- SAP SuccessFactors: Employee-initiated separation with manager approval
- Workday HCM: Self-service termination with workflow automation
- Oracle HCM Cloud: Voluntary termination with asset return process

Purpose:
- Allow employees to request their own retirement/separation
- Manager/Admin approval workflow
- Track asset handover and access revocation
- Maintain complete audit trail for compliance (SOX, GDPR, ISO 55001)

Workflow:
1. Employee submits retirement request
2. Manager/Admin reviews and approves/rejects
3. Admin processes approved requests
4. Asset handover and compliance checklist
5. Final account deactivation

Security:
- Multi-tenancy enforcement (company-scoped operations)
- Role-based access (User can request, Manager/Admin approve, Admin process)
- Complete audit logging for all retirement events
- Atomic transactions (all-or-nothing)

Performance:
- Optimized queries with select_related/prefetch_related
- Bulk operations where applicable
- Minimal database hits

Author: AI Software Engineer
Date: January 2025
"""

from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import date, timedelta
import logging

from users.models import User, UserRetirement
from assets.models import Asset
from assets.services.transfers import initiate_transfer
from audit.utils import log_audit

logger = logging.getLogger(__name__)


class UserRetirementService:
    """
    WORLD-CLASS: Self-Service User Retirement Workflow Service

    Self-Service Workflow:
    1. Submit: Employee submits retirement request
    2. Review: Manager/Admin approves or rejects
    3. Process: Admin starts processing approved requests
    4. Handover: Asset collection and reassignment
    5. Complete: Final compliance check and account deactivation
    """
    
    @classmethod
    @transaction.atomic
    def submit_retirement_request(
        cls,
        *,
        user: User,
        effective_date: date,
        reason_category: str,
        reason: str,
        notes: str = ""
    ) -> Dict:
        """
        Employee submits their own retirement request (self-service)
        
        Args:
            user: Employee submitting request
            effective_date: Desired last working day
            reason_category: Category (resignation, retirement, etc.)
            reason: Detailed reason for retirement
            notes: Additional notes (optional)
            
        Returns:
            dict with retirement request summary
            
        Raises:
            ValidationError: If validation fails
            
        Security:
            - Multi-tenancy: Automatically scoped to user's company
            - Any authenticated user can submit
            - Validates effective date (min 2 weeks notice)
            - Prevents duplicate pending requests
        """
        logger.info(f"User {user.id} submitting retirement request, effective: {effective_date}")
        
        # Validation
        if not user.is_active:
            raise ValidationError("Cannot submit retirement request - account is already inactive")
        
        # Check for existing pending request
        existing_request = UserRetirement.objects.filter(
            user=user,
            company=user.company,
            status__in=[
                UserRetirement.STATUS_REQUESTED,
                UserRetirement.STATUS_PENDING_APPROVAL,
                UserRetirement.STATUS_APPROVED,
                UserRetirement.STATUS_IN_PROGRESS,
                UserRetirement.STATUS_ASSET_HANDOVER,
                UserRetirement.STATUS_FINAL_REVIEW
            ]
        ).first()
        
        if existing_request:
            raise ValidationError(
                f"You already have a pending retirement request (Status: {existing_request.get_status_display()})"
            )
        
        # Validate effective date (minimum 2 weeks notice)
        today = date.today()
        min_notice_date = today + timedelta(days=14)
        
        if effective_date < min_notice_date:
            raise ValidationError(
                f"Effective date must be at least 2 weeks from today (minimum: {min_notice_date.strftime('%Y-%m-%d')})"
            )
        
        # Validate reason
        if not reason or len(reason.strip()) < 10:
            raise ValidationError("Retirement reason must be at least 10 characters")
        
        # Validate reason category
        valid_categories = [choice[0] for choice in UserRetirement.REASON_CATEGORY_CHOICES]
        if reason_category not in valid_categories:
            raise ValidationError(f"Invalid reason category. Must be one of: {', '.join(valid_categories)}")
        
        # Count user's assigned assets
        assigned_assets = Asset.objects.filter(
            assigned_to=user,
            company=user.company,
            status__in=[Asset.STATUS_ACTIVE, Asset.STATUS_IN_MAINTENANCE]
        ).select_related('category', 'branch')
        
        asset_count = assigned_assets.count()
        
        # Create retirement request
        retirement = UserRetirement.objects.create(
            user=user,
            company=user.company,
            requested_by=user,
            request_date=timezone.now(),
            effective_date=effective_date,
            reason_category=reason_category,
            reason=reason.strip(),
            notes=notes.strip() if notes else "",
            asset_count=asset_count,
            assets_pending=asset_count,
            status=UserRetirement.STATUS_REQUESTED
        )
        
        # Audit log
        log_audit(
            user=user,
            action='retirement_request_submitted',
            details=f"Retirement request submitted. Effective date: {effective_date}, Reason: {reason_category}, Assets: {asset_count}",
            company=user.company,
            metadata={
                'retirement_id': str(retirement.id),
                'effective_date': effective_date.isoformat(),
                'reason_category': reason_category,
                'asset_count': asset_count,
                'days_until_effective': (effective_date - today).days
            }
        )
        
        logger.info(f"Retirement request created: {retirement.id}, status: {retirement.status}")
        
        # Prepare asset list for response
        assets_list = []
        for asset in assigned_assets[:50]:  # Limit to first 50 for performance
            asset_name = asset.category.name
            if asset.dynamic_data and isinstance(asset.dynamic_data, dict):
                asset_name = asset.dynamic_data.get('name', asset.category.name)
            
            assets_list.append({
                'id': asset.id,
                'uuid': str(asset.uuid),
                'name': asset_name,
                'category': asset.category.name,
                'branch': asset.branch.name if asset.branch else 'Unassigned',
                'status': asset.status
            })
        
        return {
            'success': True,
            'retirement_id': str(retirement.id),
            'status': retirement.status,
            'status_display': retirement.get_status_display(),
            'effective_date': effective_date.isoformat(),
            'days_until_effective': retirement.days_until_effective,
            'asset_count': asset_count,
            'assets': assets_list,
            'message': 'Retirement request submitted successfully. Your manager will review your request.'
        }
    
    @classmethod
    @transaction.atomic
    def approve_retirement_request(
        cls,
        *,
        retirement_id: str,
        approver: User,
        comments: str = ""
    ) -> Dict:
        """
        Manager/Admin approves retirement request
        
        Args:
            retirement_id: UUID of retirement request
            approver: Manager or Admin approving request
            comments: Optional approval comments
            
        Returns:
            dict with approval summary
            
        Raises:
            ValidationError: If validation fails
            PermissionDenied: If approver lacks permission
            
        Security:
            - Multi-tenancy: Must be same company
            - RBAC: Manager or Admin role required
            - Cannot approve own request
        """
        logger.info(f"User {approver.id} approving retirement request {retirement_id}")
        
        # Get retirement record
        try:
            retirement = UserRetirement.objects.select_related(
                'user', 'company', 'requested_by'
            ).get(id=retirement_id)
        except UserRetirement.DoesNotExist:
            raise ValidationError("Retirement request not found")
        
        # Permission checks
        if approver.role not in [User.MANAGER, User.ADMIN]:
            raise PermissionDenied("Only Managers and Admins can approve retirement requests")
        
        if approver.company != retirement.company:
            raise PermissionDenied("Cannot approve retirement requests from different companies")
        
        if approver == retirement.user:
            raise ValidationError("Cannot approve your own retirement request")
        
        # Status check
        if not retirement.can_be_approved:
            raise ValidationError(
                f"Cannot approve - request status is {retirement.get_status_display()}"
            )
        
        # Update retirement record
        retirement.status = UserRetirement.STATUS_APPROVED
        retirement.reviewed_by = approver
        retirement.reviewed_at = timezone.now()
        retirement.approval_notes = comments.strip() if comments else ""
        retirement.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'approval_notes'])
        
        # Audit log
        log_audit(
            user=approver,
            action='retirement_request_approved',
            details=f"Retirement request approved by {approver.get_full_name()}. Effective date: {retirement.effective_date}",
            company=retirement.company,
            related_user=retirement.user,
            metadata={
                'retirement_id': str(retirement.id),
                'approver_role': approver.role,
                'comments': comments,
                'days_until_effective': retirement.days_until_effective
            }
        )
        
        logger.info(f"Retirement request {retirement_id} approved by {approver.id}")
        
        return {
            'success': True,
            'retirement_id': str(retirement.id),
            'status': retirement.status,
            'status_display': retirement.get_status_display(),
            'approved_by': approver.get_full_name(),
            'approved_at': retirement.reviewed_at.isoformat(),
            'user': {
                'id': retirement.user.id,
                'name': retirement.user.get_full_name(),
                'email': retirement.user.email
            },
            'effective_date': retirement.effective_date.isoformat(),
            'days_until_effective': retirement.days_until_effective,
            'message': 'Retirement request approved successfully'
        }
    
    @classmethod
    @transaction.atomic
    def reject_retirement_request(
        cls,
        *,
        retirement_id: str,
        reviewer: User,
        rejection_reason: str
    ) -> Dict:
        """
        Manager/Admin rejects retirement request
        
        Args:
            retirement_id: UUID of retirement request
            reviewer: Manager or Admin rejecting request
            rejection_reason: Reason for rejection
            
        Returns:
            dict with rejection summary
            
        Raises:
            ValidationError: If validation fails
            PermissionDenied: If reviewer lacks permission
        """
        logger.info(f"User {reviewer.id} rejecting retirement request {retirement_id}")
        
        # Get retirement record
        try:
            retirement = UserRetirement.objects.select_related(
                'user', 'company'
            ).get(id=retirement_id)
        except UserRetirement.DoesNotExist:
            raise ValidationError("Retirement request not found")
        
        # Permission checks
        if reviewer.role not in [User.MANAGER, User.ADMIN]:
            raise PermissionDenied("Only Managers and Admins can reject retirement requests")
        
        if reviewer.company != retirement.company:
            raise PermissionDenied("Cannot reject retirement requests from different companies")
        
        # Status check
        if not retirement.can_be_approved:
            raise ValidationError(
                f"Cannot reject - request status is {retirement.get_status_display()}"
            )
        
        # Validate rejection reason
        if not rejection_reason or len(rejection_reason.strip()) < 10:
            raise ValidationError("Rejection reason must be at least 10 characters")
        
        # Update retirement record
        retirement.status = UserRetirement.STATUS_REJECTED
        retirement.reviewed_by = reviewer
        retirement.reviewed_at = timezone.now()
        retirement.rejection_reason = rejection_reason.strip()
        retirement.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason'])
        
        # Audit log
        log_audit(
            user=reviewer,
            action='retirement_request_rejected',
            related_user=retirement.user,
            details=f"Retirement request rejected by {reviewer.get_full_name()}. Reason: {rejection_reason[:100]}",
            company=retirement.company,
            metadata={
                'retirement_id': str(retirement.id),
                'reviewer_role': reviewer.role,
                'rejection_reason': rejection_reason
            }
        )
        
        logger.info(f"Retirement request {retirement_id} rejected by {reviewer.id}")
        
        return {
            'success': True,
            'retirement_id': str(retirement.id),
            'status': retirement.status,
            'status_display': retirement.get_status_display(),
            'rejected_by': reviewer.get_full_name(),
            'rejected_at': retirement.reviewed_at.isoformat(),
            'rejection_reason': rejection_reason,
            'user': {
                'id': retirement.user.id,
                'name': retirement.user.get_full_name(),
                'email': retirement.user.email
            },
            'message': 'Retirement request rejected'
        }
    
    @classmethod
    @transaction.atomic
    def cancel_retirement_request_by_user(
        cls,
        *,
        retirement_id: str,
        user: User,
        reason: str
    ) -> Dict:
        """
        Employee cancels their own retirement request
        
        Args:
            retirement_id: UUID of retirement request
            user: Employee canceling request
            reason: Reason for cancellation
            
        Returns:
            dict with cancellation summary
            
        Raises:
            ValidationError: If validation fails
            PermissionDenied: If user is not request owner
        """
        logger.info(f"User {user.id} canceling retirement request {retirement_id}")
        
        # Get retirement record
        try:
            retirement = UserRetirement.objects.select_related('user', 'company').get(id=retirement_id)
        except UserRetirement.DoesNotExist:
            raise ValidationError("Retirement request not found")
        
        # Permission check - can only cancel own request
        if retirement.user != user:
            raise PermissionDenied("You can only cancel your own retirement request")
        
        if retirement.company != user.company:
            raise PermissionDenied("Cannot cancel retirement request from different company")
        
        # Status check - can only cancel before completion
        if not retirement.can_be_cancelled:
            raise ValidationError(
                f"Cannot cancel - request status is {retirement.get_status_display()}"
            )
        
        # Validate reason
        if not reason or len(reason.strip()) < 10:
            raise ValidationError("Cancellation reason must be at least 10 characters")
        
        # Update retirement record
        old_status = retirement.status
        retirement.status = UserRetirement.STATUS_CANCELLED
        retirement.notes += f"\n\nCancelled by {user.get_full_name()} on {timezone.now().isoformat()}\nReason: {reason}"
        retirement.save(update_fields=['status', 'notes'])
        
        # Audit log
        log_audit(
            user=user,
            action='retirement_request_cancelled_by_user',
            details=f"Retirement request cancelled by employee. Previous status: {old_status}. Reason: {reason}",
            company=retirement.company,
            metadata={
                'retirement_id': str(retirement.id),
                'previous_status': old_status,
                'cancellation_reason': reason
            }
        )
        
        logger.info(f"Retirement request {retirement_id} cancelled by user {user.id}")
        
        return {
            'success': True,
            'retirement_id': str(retirement.id),
            'status': retirement.status,
            'status_display': retirement.get_status_display(),
            'message': 'Retirement request cancelled successfully'
        }
    
    @classmethod
    @transaction.atomic
    def start_retirement_processing(
        cls,
        *,
        retirement_id: str,
        admin: User
    ) -> Dict:
        """
        Admin starts processing approved retirement
        
        Args:
            retirement_id: UUID of retirement request
            admin: Admin starting processing
            
        Returns:
            dict with processing status and asset list
            
        Raises:
            ValidationError: If validation fails
            PermissionDenied: If admin lacks permission
        """
        logger.info(f"Admin {admin.id} starting processing for retirement {retirement_id}")
        
        # Get retirement record
        try:
            retirement = UserRetirement.objects.select_related(
                'user', 'company'
            ).get(id=retirement_id)
        except UserRetirement.DoesNotExist:
            raise ValidationError("Retirement request not found")
        
        # Permission checks
        if admin.role != User.ADMIN:
            raise PermissionDenied("Only Admins can process retirement requests")
        
        if admin.company != retirement.company:
            raise PermissionDenied("Cannot process retirement requests from different companies")
        
        # Status check
        if retirement.status != UserRetirement.STATUS_APPROVED:
            raise ValidationError(
                f"Cannot start processing - request status is {retirement.get_status_display()}. Must be 'Approved'."
            )
        
        # Get user's assigned assets
        assigned_assets = Asset.objects.filter(
            assigned_to=retirement.user,
            company=retirement.company,
            status__in=[Asset.STATUS_ACTIVE, Asset.STATUS_IN_MAINTENANCE]
        ).select_related('category', 'branch')
        
        asset_count = assigned_assets.count()
        
        # Update retirement record
        retirement.status = UserRetirement.STATUS_IN_PROGRESS
        retirement.processed_by = admin
        retirement.processing_started_at = timezone.now()
        retirement.asset_count = asset_count
        retirement.assets_pending = asset_count
        retirement.save(update_fields=[
            'status', 'processed_by', 'processing_started_at',
            'asset_count', 'assets_pending'
        ])
        
        # Audit log
        log_audit(
            user=admin,
            action='retirement_processing_started',
            related_user=retirement.user,
            details=f"Retirement processing started by {admin.get_full_name()}. {asset_count} assets to process.",
            company=retirement.company,
            metadata={
                'retirement_id': str(retirement.id),
                'asset_count': asset_count,
                'effective_date': retirement.effective_date.isoformat(),
                'days_since_request': retirement.duration_days
            }
        )
        
        logger.info(f"Retirement processing started for {retirement_id}, {asset_count} assets found")
        
        # Prepare asset list
        assets_list = []
        for asset in assigned_assets:
            asset_name = asset.category.name
            if asset.dynamic_data and isinstance(asset.dynamic_data, dict):
                asset_name = asset.dynamic_data.get('name', asset.category.name)
            
            assets_list.append({
                'id': asset.id,
                'uuid': str(asset.uuid),
                'name': asset_name,
                'category': asset.category.name,
                'branch': asset.branch.name if asset.branch else 'Unassigned',
                'status': asset.status,
                'current_value': float(asset.current_value) if asset.current_value else 0.0
            })
        
        return {
            'success': True,
            'retirement_id': str(retirement.id),
            'status': retirement.status,
            'status_display': retirement.get_status_display(),
            'user': {
                'id': retirement.user.id,
                'name': retirement.user.get_full_name(),
                'email': retirement.user.email,
                'role': retirement.user.get_role_display()
            },
            'asset_count': asset_count,
            'assets': assets_list,
            'effective_date': retirement.effective_date.isoformat(),
            'days_until_effective': retirement.days_until_effective,
            'message': 'Retirement processing started. Please proceed with asset handover.'
        }
