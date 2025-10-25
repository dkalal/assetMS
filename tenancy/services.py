"""
Branch Manager Assignment Service

Provides business logic for managing branch manager assignments with
comprehensive audit logging, notifications, and validation.
"""
from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit.utils import log_audit
from tenancy.models import Alert, Branch, Company

User = get_user_model()


class BranchManagerService:
    """
    Service class for managing branch manager assignments.
    
    Provides atomic operations for assigning, removing, and transferring
    branch managers with full audit trail and notifications.
    
    Security:
    - All operations are atomic (transaction.atomic)
    - Company scoping enforced
    - Role validation performed
    - Comprehensive audit logging
    - User notifications sent
    
    Usage:
        service = BranchManagerService()
        service.assign_manager(
            branch=branch,
            new_manager=user,
            assigned_by=admin,
            notes="Quarterly rotation"
        )
    """
    
    @staticmethod
    def assign_manager(
        branch: Branch,
        new_manager: User,
        assigned_by: User,
        notes: Optional[str] = None,
        notify_users: bool = True
    ) -> Branch:
        """
        Assign a manager to a branch with full audit trail.
        
        Process:
        1. Validate manager belongs to company
        2. Validate manager has appropriate role
        3. Notify current manager (if exists)
        4. Update branch.manager
        5. Create audit log
        6. Notify new manager
        7. Return updated branch
        
        Args:
            branch: Branch to assign manager to
            new_manager: User to assign as manager
            assigned_by: Admin user making the assignment
            notes: Optional notes about the assignment
            notify_users: Whether to send notifications (default: True)
        
        Returns:
            Branch: Updated branch instance
        
        Raises:
            ValidationError: If validation fails
        """
        with transaction.atomic():
            old_manager = branch.manager
            
            # Validation: Manager belongs to company
            if new_manager.company != branch.company:
                raise ValidationError(
                    f"Manager {new_manager.username} must belong to "
                    f"the same company as the branch ({branch.company.name})."
                )
            
            # Validation: Manager has appropriate role
            if hasattr(new_manager, 'role'):
                valid_roles = ['admin', 'manager']
                if new_manager.role not in valid_roles:
                    raise ValidationError(
                        f"User {new_manager.username} must have 'manager' or 'admin' role. "
                        f"Current role: {new_manager.get_role_display()}"
                    )
            
            # Update branch manager
            branch.manager = new_manager
            branch.manager_assigned_at = timezone.now()
            branch.manager_assigned_by = assigned_by
            
            # Store transition notes in metadata
            if notes:
                if 'manager_history' not in branch.metadata:
                    branch.metadata['manager_history'] = []
                branch.metadata['manager_history'].append({
                    'from_manager_id': old_manager.pk if old_manager else None,
                    'from_manager_username': old_manager.username if old_manager else None,
                    'to_manager_id': new_manager.pk,
                    'to_manager_username': new_manager.username,
                    'assigned_by_id': assigned_by.pk,
                    'assigned_by_username': assigned_by.username,
                    'assigned_at': timezone.now().isoformat(),
                    'notes': notes,
                })
            
            branch.save()
            
            # Audit log
            log_audit(
                assigned_by,
                "branch_manager_assigned",
                details=(
                    f"Assigned {new_manager.get_full_name() or new_manager.username} "
                    f"as manager of branch '{branch.name}'"
                    + (f". Previous manager: {old_manager.username}" if old_manager else "")
                    + (f". Notes: {notes}" if notes else "")
                ),
                company=branch.company,
                branch=branch,
                related_user=new_manager,
                metadata={
                    'old_manager_id': old_manager.pk if old_manager else None,
                    'old_manager_username': old_manager.username if old_manager else None,
                    'new_manager_id': new_manager.pk,
                    'new_manager_username': new_manager.username,
                    'branch_id': branch.pk,
                    'branch_name': branch.name,
                    'branch_code': branch.code,
                    'assigned_by_id': assigned_by.pk,
                    'assigned_by_username': assigned_by.username,
                    'notes': notes,
                }
            )
            
            # Notifications
            if notify_users:
                # Notify old manager
                if old_manager and old_manager != new_manager:
                    Alert.objects.create(
                        company=branch.company,
                        branch=branch,
                        recipient=old_manager,
                        level=Alert.LEVEL_INFO,
                        message=(
                            f"You are no longer the manager of '{branch.name}'. "
                            f"{new_manager.get_full_name() or new_manager.username} "
                            f"has been assigned as the new manager."
                        ),
                        context={
                            'branch_id': branch.pk,
                            'branch_name': branch.name,
                            'new_manager_id': new_manager.pk,
                            'new_manager_name': new_manager.get_full_name() or new_manager.username,
                            'assigned_by': assigned_by.get_full_name() or assigned_by.username,
                            'timestamp': timezone.now().isoformat(),
                            'notes': notes,
                        }
                    )
                
                # Notify new manager
                Alert.objects.create(
                    company=branch.company,
                    branch=branch,
                    recipient=new_manager,
                    level=Alert.LEVEL_INFO,
                    message=(
                        f"You have been assigned as the manager of '{branch.name}'. "
                        f"You are now responsible for managing this branch's assets and staff."
                    ),
                    context={
                        'branch_id': branch.pk,
                        'branch_name': branch.name,
                        'branch_code': branch.code,
                        'assigned_by': assigned_by.get_full_name() or assigned_by.username,
                        'timestamp': timezone.now().isoformat(),
                        'notes': notes,
                    }
                )
            
            return branch
    
    @staticmethod
    def remove_manager(
        branch: Branch,
        removed_by: User,
        reason: Optional[str] = None,
        notify_user: bool = True
    ) -> Branch:
        """
        Remove the current manager from a branch.
        
        Args:
            branch: Branch to remove manager from
            removed_by: Admin user removing the manager
            reason: Optional reason for removal
            notify_user: Whether to notify the removed manager
        
        Returns:
            Branch: Updated branch instance
        """
        with transaction.atomic():
            old_manager = branch.manager
            
            if not old_manager:
                raise ValidationError("Branch has no manager to remove.")
            
            # Update branch
            branch.manager = None
            branch.manager_assigned_at = None
            
            # Store removal in metadata
            if 'manager_history' not in branch.metadata:
                branch.metadata['manager_history'] = []
            branch.metadata['manager_history'].append({
                'action': 'removed',
                'manager_id': old_manager.pk,
                'manager_username': old_manager.username,
                'removed_by_id': removed_by.pk,
                'removed_by_username': removed_by.username,
                'removed_at': timezone.now().isoformat(),
                'reason': reason,
            })
            
            branch.save()
            
            # Audit log
            log_audit(
                removed_by,
                "branch_manager_removed",
                details=(
                    f"Removed {old_manager.get_full_name() or old_manager.username} "
                    f"as manager of branch '{branch.name}'"
                    + (f". Reason: {reason}" if reason else "")
                ),
                company=branch.company,
                branch=branch,
                related_user=old_manager,
                metadata={
                    'manager_id': old_manager.pk,
                    'manager_username': old_manager.username,
                    'branch_id': branch.pk,
                    'branch_name': branch.name,
                    'removed_by_id': removed_by.pk,
                    'removed_by_username': removed_by.username,
                    'reason': reason,
                }
            )
            
            # Notification
            if notify_user:
                Alert.objects.create(
                    company=branch.company,
                    branch=branch,
                    recipient=old_manager,
                    level=Alert.LEVEL_WARNING,
                    message=(
                        f"You have been removed as manager of '{branch.name}'"
                        + (f". Reason: {reason}" if reason else ".")
                    ),
                    context={
                        'branch_id': branch.pk,
                        'branch_name': branch.name,
                        'removed_by': removed_by.get_full_name() or removed_by.username,
                        'timestamp': timezone.now().isoformat(),
                        'reason': reason,
                    }
                )
            
            return branch
    
    @staticmethod
    def get_manager_statistics(manager: User, company: Company) -> dict:
        """
        Get statistics for a manager's performance.
        
        Args:
            manager: Manager user
            company: Company context
        
        Returns:
            dict: Statistics including branch count, asset count, etc.
        """
        from assets.models import Asset
        
        managed_branches = Branch.objects.filter(
            manager=manager,
            company=company,
            is_active=True
        )
        
        total_assets = Asset.objects.filter(
            branch__in=managed_branches,
            company=company
        ).count()
        
        total_staff = User.objects.filter(
            user_branches__branch__in=managed_branches,
            company=company,
            is_active=True
        ).distinct().count()
        
        return {
            'manager': manager,
            'branch_count': managed_branches.count(),
            'branches': list(managed_branches),
            'total_assets': total_assets,
            'total_staff': total_staff,
            'experience_days': (
                (timezone.now() - managed_branches.first().manager_assigned_at).days
                if managed_branches.exists() and managed_branches.first().manager_assigned_at
                else 0
            ),
        }
