"""
Approval Workflow Views

Provides views for creating, reviewing, and managing approval requests.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from tenancy.approval_models import ApprovalRequest
from tenancy.mixins import BranchContextMixin
from tenancy.models import Branch

from audit.utils import log_audit

User = get_user_model()


class ApprovalDashboardView(LoginRequiredMixin, BranchContextMixin, TemplateView):
    """
    Dashboard for viewing and managing approval requests.
    
    Shows:
    - Pending approvals assigned to user (asset creation & disposal only)
    - Requests created by user
    - Recent approval activity
    - Statistics
    
    Security:
    - Managers see requests for their branches
    - Admins see all company requests
    - Users see only their own requests
    
    URL: /tenancy/approvals/
    Template: tenancy/approval_dashboard_worldclass.html
    """
    template_name = "tenancy/approval_dashboard_worldclass.html"

    def get_context_data(self, **kwargs):
        """Prepare approval dashboard data."""
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "company", None)
        user = self.request.user
        user_role = getattr(user, 'role', None)
        
        # Get managed branches if user is a manager
        managed_branches = Branch.objects.filter(
            manager=user,
            company=company,
            is_active=True
        ) if user_role == 'manager' else Branch.objects.none()
        
        # Pending approvals assigned to user
        if user_role == 'admin':
            # Admins see all pending requests
            pending_approvals = ApprovalRequest.objects.filter(
                company=company,
                status=ApprovalRequest.STATUS_PENDING
            ).select_related('branch', 'requested_by', 'assigned_to').order_by('-created_at')
        elif user_role == 'manager':
            # Managers see requests for their branches
            pending_approvals = ApprovalRequest.objects.filter(
                company=company,
                branch__in=managed_branches,
                status=ApprovalRequest.STATUS_PENDING
            ).select_related('branch', 'requested_by', 'assigned_to').order_by('-created_at')
        else:
            # Regular users see no pending approvals
            pending_approvals = ApprovalRequest.objects.none()
        
        # Requests created by user
        my_requests = ApprovalRequest.objects.filter(
            company=company,
            requested_by=user
        ).select_related('branch', 'assigned_to', 'approved_by').order_by('-created_at')[:10]
        
        # Recent activity (approved/rejected in last 7 days)
        from datetime import timedelta
        from django.utils import timezone
        
        recent_activity = ApprovalRequest.objects.filter(
            company=company,
            status__in=[ApprovalRequest.STATUS_APPROVED, ApprovalRequest.STATUS_REJECTED],
            updated_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('branch', 'requested_by', 'approved_by').order_by('-updated_at')[:10]
        
        # Statistics
        total_pending = pending_approvals.count()
        overdue_count = sum(1 for req in pending_approvals if req.is_overdue)
        
        context.update({
            'pending_approvals': pending_approvals,
            'my_requests': my_requests,
            'recent_activity': recent_activity,
            'total_pending': total_pending,
            'overdue_count': overdue_count,
            'can_approve': user_role in ['admin', 'manager'],
            'today': timezone.now(),
        })
        
        return context


class ApprovalRequestCreateView(LoginRequiredMixin, BranchContextMixin, CreateView):
    """View for creating new approval requests.
    
    Security:
    - Users can only create requests for their branches
    - Automatically assigns to branch manager
    - Company-scoped
    
    URL: /tenancy/approvals/create/
    Template: tenancy/approval_request_form.html
    """
    model = ApprovalRequest
    template_name = "tenancy/approval_request_form.html"
    fields = ['request_type', 'title', 'description', 'branch', 'priority', 'deadline', 'metadata']
    
    def get_form(self, form_class=None):
        """Customize form to scope branches to user's company."""
        form = super().get_form(form_class)
        company = getattr(self.request, "company", None)
        
        # Scope branches to company
        form.fields['branch'].queryset = Branch.objects.filter(
            company=company,
            is_active=True
        ).order_by('name')
        
        # Limit request types exposed in this generic form.
        # Asset creation/disposal workflows have dedicated views that
        # capture full asset metadata. To avoid broken approvals,
        # hide those system-managed types here.
        request_type_field = form.fields.get('request_type')
        if request_type_field is not None:
            disallowed_types = {
                ApprovalRequest.TYPE_ASSET_CREATION,
                ApprovalRequest.TYPE_ASSET_DISPOSAL,
            }
            request_type_field.choices = [
                (value, label)
                for (value, label) in request_type_field.choices
                if value not in disallowed_types
            ]
        
        # Add CSS classes and configure widgets
        for field_name, field in form.fields.items():
            if field_name == 'deadline':
                # Configure deadline field with proper attributes
                field.widget.attrs.update({
                    'class': 'form-control',
                    'aria-describedby': 'deadline-help deadline-summary',
                    'aria-labelledby': form.fields['deadline'].label or 'deadline-label'
                })
            else:
                field.widget.attrs['class'] = 'form-control'
        
        return form
    
    def form_valid(self, form):
        """Set additional fields before saving."""
        company = getattr(self.request, "company", None)
        
        form.instance.company = company
        form.instance.requested_by = self.request.user
        
        # Auto-assign to branch manager if exists
        branch = form.instance.branch
        if branch.manager:
            form.instance.assigned_to = branch.manager
        else:
            # Assign to first admin if no branch manager
            admin = User.objects.filter(
                company=company,
                role='admin',
                is_active=True
            ).first()
            if admin:
                form.instance.assigned_to = admin
        
        response = super().form_valid(form)
        
        # Create notification for assigned user
        if form.instance.assigned_to:
            from tenancy.models import Alert
            Alert.objects.create(
                company=company,
                branch=branch,
                recipient=form.instance.assigned_to,
                level=Alert.LEVEL_INFO,
                message=f"New approval request assigned to you: {form.instance.title}",
                context={
                    'request_id': form.instance.pk,
                    'request_type': form.instance.request_type,
                    'requested_by': self.request.user.pk,
                }
            )
        
        # Log audit event
        log_audit(
            self.request.user,
            "approval_request_created",
            details=f"Created approval request: {form.instance.title}",
            company=company,
            branch=branch,
            metadata={
                'request_id': form.instance.pk,
                'request_type': form.instance.request_type,
                'title': form.instance.title,
            }
        )
        
        messages.success(
            self.request,
            f"Approval request '{form.instance.title}' created successfully."
        )
        
        return response
    
    def get_success_url(self):
        """Redirect to approval dashboard."""
        return reverse('approval_dashboard')


class ApprovalRequestDetailView(LoginRequiredMixin, BranchContextMixin, DetailView):
    """
    Detailed view of an approval request.
    
    Security:
    - Users can only view requests they created or are assigned to
    - Company-scoped
    
    URL: /tenancy/approvals/<pk>/
    Template: tenancy/approval_request_detail.html
    """
    model = ApprovalRequest
    template_name = "tenancy/approval_request_detail.html"
    context_object_name = 'approval_request'
    
    def get_queryset(self):
        """Scope to company and user permissions."""
        company = getattr(self.request, "company", None)
        user = self.request.user
        user_role = getattr(user, 'role', None)
        
        if user_role == 'admin':
            # Admins see all requests
            return ApprovalRequest.objects.filter(company=company)
        elif user_role == 'manager':
            # Managers see requests for their branches or assigned to them
            managed_branches = Branch.objects.filter(manager=user, company=company)
            return ApprovalRequest.objects.filter(
                company=company
            ).filter(
                models.Q(branch__in=managed_branches) |
                models.Q(assigned_to=user) |
                models.Q(requested_by=user)
            )
        else:
            # Regular users see only their requests
            return ApprovalRequest.objects.filter(
                company=company,
                requested_by=user
            )

    def get_context_data(self, **kwargs):
        """Inject permissions and ensure HttpRequest remains available."""
        context = super().get_context_data(**kwargs)
        approval_request = context.get('approval_request', context.get('object'))

        user = self.request.user
        user_role = getattr(user, 'role', None)

        # CRITICAL: Separation of Duties - Requester cannot approve their own request
        is_requester = (approval_request.requested_by == user)
        
        # Check if user has approval authority
        branch = getattr(approval_request, 'branch', None)
        has_approval_authority = (
            user_role == 'admin'
            or getattr(approval_request, 'assigned_to', None) == user
            or (
                user_role == 'manager'
                and branch is not None
                and getattr(branch, 'manager_id', None) == user.id
            )
        )
        
        # Can approve only if has authority AND is not the requester
        can_approve = has_approval_authority and not is_requester
        
        # Determine user's relationship to this request
        if is_requester:
            user_relationship = 'requester'
        elif approval_request.assigned_to == user:
            user_relationship = 'approver'
        elif user_role == 'admin':
            user_relationship = 'admin'
        else:
            user_relationship = 'viewer'

        context['can_approve'] = can_approve
        context['is_requester'] = is_requester
        context['user_relationship'] = user_relationship
        context['approval_request'] = approval_request
        context['request'] = self.request
        return context


class ApprovalActionView(LoginRequiredMixin, BranchContextMixin, View):
    """
    Handle approval actions (approve, reject, escalate).
    
    Security:
    - Only assigned user or admins can take action
    - Company-scoped
    - Atomic transactions
    
    URL: /tenancy/approvals/<pk>/action/
    """
    
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Process approval action."""
        import logging
        logger = logging.getLogger(__name__)
        
        company = getattr(request, "company", None)
        user = request.user
        user_role = getattr(user, 'role', None)
        
        # Get approval request
        try:
            approval_request = get_object_or_404(
                ApprovalRequest,
                pk=pk,
                company=company
            )
        except Exception as e:
            logger.error(f"Error getting approval request: {e}")
            raise
        
        # CRITICAL: Separation of Duties - Requester cannot approve their own request
        
        if approval_request.requested_by == user:
            logger.warning(f"SECURITY VIOLATION: User {user.username} attempted to approve own request")
            messages.error(
                request,
                "Security Violation: You cannot approve your own request. "
                "This action has been logged for audit purposes."
            )
            # Log security violation
            log_audit(
                user,
                'security_violation',
                details=f'User attempted to approve their own request: {approval_request.title}',
                company=company,
                branch=approval_request.branch,
                metadata={
                    'request_id': approval_request.pk,
                    'violation_type': 'self_approval_attempt',
                    'request_type': approval_request.request_type,
                }
            )
            return redirect('approval_request_detail', pk=pk)
        
        # Check approval authority
        has_approval_authority = (
            user_role == 'admin' or
            approval_request.assigned_to == user or
            (user_role == 'manager' and approval_request.branch.manager == user)
        )
        
        if not has_approval_authority:
            logger.warning(f"User {user.username} does not have approval authority")
            messages.error(request, "You do not have permission to take action on this request.")
            return redirect('approval_dashboard')
        
        # Get action and normalize for robust handling
        raw_action = request.POST.get('action')
        action = (raw_action or '').strip().lower()
        if action == 'approve':
            notes = request.POST.get('notes', '')
            
            try:
                with transaction.atomic():
                    # Approve the request
                    approval_request.approve(approved_by=user, notes=notes)
                    
                    # If this is an asset creation request, create the asset
                    if approval_request.request_type == approval_request.TYPE_ASSET_CREATION:
                        metadata = approval_request.metadata or {}
                        asset_data = metadata.get('asset_data')
                        if asset_data:
                            try:
                                asset = approval_request.create_asset_from_approval()
                                messages.success(
                                    request,
                                    f"Request approved. Asset '{asset}' created successfully. "
                                    f"<a href='/assets/{asset.uuid}/' class='alert-link'>View Asset</a>",
                                    extra_tags='safe'
                                )
                            except Exception as e:
                                # Log detailed error
                                import logging
                                import traceback
                                logger = logging.getLogger(__name__)
                                logger.error(f"Asset creation failed for request {approval_request.pk}: {str(e)}")
                                logger.error(traceback.format_exc())
                                
                                messages.error(
                                    request,
                                    f"Request approved but asset creation failed: {str(e)}. "
                                    f"Please check the logs or contact support."
                                )
                        else:
                            logger.warning(
                                "Asset creation request %s has no 'asset_data' in metadata. "
                                "Treating as approval-only workflow.",
                                approval_request.pk,
                            )
                            messages.warning(
                                request,
                                "Request approved successfully, but no asset record was created "
                                "because this request does not contain structured asset details. "
                                "Please register the asset manually from the Assets page."
                            )
                    
                    # If this is an asset disposal request, dispose the asset
                    elif approval_request.request_type == approval_request.TYPE_ASSET_DISPOSAL:
                        metadata = approval_request.metadata or {}
                        asset_id = metadata.get('asset_id')
                        if asset_id:
                            try:
                                asset = approval_request.execute_asset_disposal()
                                messages.success(
                                    request,
                                    f"Request approved. Asset '{asset}' has been disposed successfully."
                                )
                            except Exception as e:
                                import logging
                                import traceback
                                logger = logging.getLogger(__name__)
                                logger.error(f"Asset disposal failed for request {approval_request.pk}: {str(e)}")
                                logger.error(traceback.format_exc())
                                
                                messages.error(
                                    request,
                                    f"Request approved but asset disposal failed: {str(e)}. "
                                    f"Please check the logs or contact support."
                                )
                        else:
                            logger.warning(
                                "Asset disposal request %s has no 'asset_id' in metadata. "
                                "Treating as approval-only workflow.",
                                approval_request.pk,
                            )
                            messages.warning(
                                request,
                                "Request approved successfully, but no asset record was updated "
                                "because this request is not linked to a specific asset."
                            )
                    
                    else:
                        messages.success(request, f"Request '{approval_request.title}' approved successfully.")
                        
            except Exception as e:
                # Catch any approval errors
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.error(f"Approval failed for request {approval_request.pk}: {str(e)}")
                logger.error(traceback.format_exc())
                
                messages.error(
                    request,
                    f"Approval failed: {str(e)}. Please try again or contact support."
                )
        
        elif action == 'reject':
            # Get reason from notes field (same field used for both approve and reject)
            reason = request.POST.get('notes', '') or request.POST.get('reason', '')
            if not reason or not reason.strip():
                messages.error(request, "Rejection reason is required. Please provide a reason in the notes field.")
                return redirect('approval_request_detail', pk=pk)
            
            try:
                approval_request.reject(rejected_by=user, reason=reason)
                messages.warning(request, f"Request '{approval_request.title}' has been rejected.")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Rejection failed for request {approval_request.pk}: {str(e)}")
                messages.error(request, f"Rejection failed: {str(e)}")
        
        elif action == 'escalate':
            approval_request.escalate()
            messages.info(request, f"Request '{approval_request.title}' escalated to admin.")
        
        else:
            # Unknown or missing action value – keep user-facing message simple
            logger.warning(f"Invalid action received: raw={raw_action!r}, normalized={action!r}")
            messages.error(request, "Invalid action.")
        
        return redirect('approval_dashboard')
