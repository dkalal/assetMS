from __future__ import annotations

from typing import Dict, List, Optional

from django.http import HttpRequest
from django.db.models import Q

from .models import Branch, Company, UserBranch


def tenancy_context(request: HttpRequest) -> Dict[str, Optional[Company]]:
    company: Optional[Company] = getattr(request, "company", None)
    branch: Optional[Branch] = getattr(request, "branch", None)
    memberships: List[UserBranch] = []

    user = getattr(request, "user", None)
    if company is not None and user and user.is_authenticated:
        request_memberships = getattr(request, "available_branches", None)
        if request_memberships:
            memberships = list(request_memberships)
        else:
            memberships = list(
                UserBranch.objects.select_related("branch")
                .filter(user=user, company=company, branch__is_active=True)
                .order_by("branch__name")
            )

    if branch is None and memberships:
        primary_membership = next((m for m in memberships if m.is_primary), None)
        branch = primary_membership.branch if primary_membership else memberships[0].branch

    # Calculate badge counts for navigation
    pending_maintenance_count = 0
    pending_approvals_count = 0
    
    if user and user.is_authenticated and company:
        user_role = getattr(user, 'role', 'user')
        
        # Maintenance badge (overdue + upcoming in next 7 days)
        if user_role in ('admin', 'manager'):
            from assets.models import MaintenanceRecord
            from django.utils import timezone
            from datetime import timedelta
            
            maintenance_qs = MaintenanceRecord.objects.filter(
                company=company,
                status=MaintenanceRecord.Status.SCHEDULED
            )
            
            # Scope by branch visibility
            if user_role == 'manager' and not user.is_superuser:
                if branch:
                    maintenance_qs = maintenance_qs.filter(Q(branch=branch) | Q(branch__isnull=True))
                else:
                    branch_ids = [m.branch_id for m in memberships if m.branch_id]
                    if branch_ids:
                        maintenance_qs = maintenance_qs.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
                    else:
                        maintenance_qs = maintenance_qs.filter(branch__isnull=True)
            
            now = timezone.localdate()
            upcoming_threshold = now + timedelta(days=7)
            pending_maintenance_count = maintenance_qs.filter(
                Q(scheduled_for__lt=now) | Q(scheduled_for__lte=upcoming_threshold)
            ).count()
        
        # Approvals badge (pending only)
        if user_role in ('admin', 'manager'):
            from tenancy.approval_models import ApprovalRequest
            
            approvals_qs = ApprovalRequest.objects.filter(
                company=company,
                status=ApprovalRequest.STATUS_PENDING
            )
            
            # Scope by branch visibility
            if user_role == 'manager' and not user.is_superuser:
                managed_branches = Branch.objects.filter(
                    manager=user,
                    company=company,
                    is_active=True
                )
                approvals_qs = approvals_qs.filter(branch__in=managed_branches)
            
            pending_approvals_count = approvals_qs.count()

    return {
        "active_company": company,
        "active_branch": branch,
        "available_branches": memberships,
        "pending_maintenance_count": pending_maintenance_count,
        "pending_approvals_count": pending_approvals_count,
    }
