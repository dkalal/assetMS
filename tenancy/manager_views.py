"""
Manager-specific views for branch management.

These views are accessible to users with the 'manager' role who have been
assigned to manage one or more branches.
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from tenancy.mixins import BranchContextMixin
from tenancy.models import Branch
from tenancy.reports import ManagerPerformanceReport

User = get_user_model()


class ManagerDashboardView(LoginRequiredMixin, BranchContextMixin, TemplateView):
    """
    Dashboard for branch managers to view and manage their assigned branches.
    
    This view is accessible to users with 'manager' or 'admin' role who have
    been assigned as managers to one or more branches.
    
    Features:
    - View all managed branches
    - See branch statistics (assets, staff, pending approvals)
    - View maintenance alerts
    - Quick access to branch assets
    
    Security:
    - Restricted to managers and admins
    - Only shows branches the user manages
    - Company-scoped queries
    
    URL: /tenancy/manager-dashboard/
    Template: tenancy/manager_dashboard.html
    """
    template_name = "tenancy/manager_dashboard.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Enforce manager access before processing requests."""
        if not getattr(request, "company", None):
            messages.error(request, "Company context required.")
            return redirect("dashboard")
        
        # Check if user has manager or admin role
        user_role = getattr(request.user, "role", None)
        is_manager_or_admin = user_role in ['manager', 'admin']
        is_superuser = request.user.is_superuser
        
        if not (is_manager_or_admin or is_superuser):
            messages.error(
                request,
                "You must have manager privileges to access this page."
            )
            return redirect("dashboard")
        
        # Check if user manages any branches
        manages_branches = Branch.objects.filter(
            manager=request.user,
            is_active=True
        ).exists()
        
        if not manages_branches:
            messages.warning(
                request,
                "You are not currently assigned as a manager to any branches. "
                "Contact your administrator to be assigned."
            )
            return redirect("dashboard")
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Prepare context data for manager dashboard.
        
        Returns:
            dict: Context containing managed branches with statistics
        """
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "company", None)
        user = self.request.user
        
        # Get all branches managed by this user
        managed_branches = Branch.objects.filter(
            manager=user,
            company=company,
            is_active=True
        ).select_related("company").order_by("name")
        
        # Gather statistics for each branch
        branches_data = []
        total_assets = 0
        total_staff = 0
        total_pending = 0
        total_maintenance_due = 0
        
        for branch in managed_branches:
            # Get asset count
            from assets.models import Asset
            asset_count = Asset.objects.filter(
                branch=branch,
                company=company
            ).count()
            
            # Get staff count
            from tenancy.models import UserBranch
            staff_count = UserBranch.objects.filter(
                branch=branch,
                company=company
            ).values('user').distinct().count()
            
            # Get pending approvals (transfers to this branch)
            try:
                from assets.models import AssetTransfer
                pending_approvals = AssetTransfer.objects.filter(
                    to_branch=branch,
                    state='pending'
                ).count()
            except (ImportError, Exception):
                pending_approvals = 0
            
            # Get maintenance due (next 7 days)
            # Note: Asset model doesn't have next_maintenance_date field
            # This would need to be implemented if maintenance tracking is required
            maintenance_due = 0
            
            # Get recent activity count (last 30 days)
            from audit.models import AuditLog
            recent_activity = AuditLog.objects.filter(
                branch=branch,
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            branches_data.append({
                'branch': branch,
                'asset_count': asset_count,
                'staff_count': staff_count,
                'pending_approvals': pending_approvals,
                'maintenance_due': maintenance_due,
                'recent_activity': recent_activity,
                'assigned_at': branch.manager_assigned_at,
                'assigned_by': branch.manager_assigned_by,
            })
            
            # Accumulate totals
            total_assets += asset_count
            total_staff += staff_count
            total_pending += pending_approvals
            total_maintenance_due += maintenance_due
        
        context.update({
            'managed_branches': branches_data,
            'total_branches': len(branches_data),
            'total_assets': total_assets,
            'total_staff': total_staff,
            'total_pending': total_pending,
            'total_maintenance_due': total_maintenance_due,
            'manager': user,
        })
        
        return context


class ManagerPerformanceView(LoginRequiredMixin, BranchContextMixin, TemplateView):
    """
    Performance report view for branch managers.
    
    Displays comprehensive performance metrics, analytics, and recommendations
    for managers to track their effectiveness.
    
    Features:
    - Overall compliance score and grade
    - Branch, asset, and staff metrics
    - Approval response times
    - Maintenance compliance
    - Activity trends
    - Actionable recommendations
    
    Security:
    - Restricted to managers and admins
    - Only shows data for managed branches
    - Company-scoped queries
    
    URL: /tenancy/manager-performance/
    Template: tenancy/manager_performance.html
    """
    template_name = "tenancy/manager_performance.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Enforce manager access."""
        if not getattr(request, "company", None):
            messages.error(request, "Company context required.")
            return redirect("dashboard")
        
        user_role = getattr(request.user, "role", None)
        is_manager_or_admin = user_role in ['manager', 'admin']
        
        if not (is_manager_or_admin or request.user.is_superuser):
            messages.error(request, "You must have manager privileges.")
            return redirect("dashboard")
        
        manages_branches = Branch.objects.filter(
            manager=request.user,
            is_active=True
        ).exists()
        
        if not manages_branches:
            messages.warning(request, "You are not assigned to any branches.")
            return redirect("dashboard")
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Prepare performance report data."""
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "company", None)
        user = self.request.user
        
        # Get period from query params (default 30 days)
        period_days = int(self.request.GET.get('period', 30))
        
        # Generate performance report
        report_generator = ManagerPerformanceReport(
            manager=user,
            company=company,
            period_days=period_days
        )
        
        report_data = report_generator.generate()
        
        context.update({
            'report': report_data,
            'period_days': period_days,
            'available_periods': [7, 30, 90, 180, 365],
        })
        
        return context
