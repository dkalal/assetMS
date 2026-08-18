"""
Asset Disposal Request Views

Provides secure workflow for requesting asset disposal with admin approval.
Ensures accountability and prevents accidental asset loss.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, ListView

from assets.models import Asset
from audit.utils import log_audit
from tenancy.approval_models import ApprovalRequest
from tenancy.mixins import BranchContextMixin
from tenancy.models import Branch
from users.utils import can


class AssetDisposalRequestView(LoginRequiredMixin, BranchContextMixin, CreateView):
    """
    View for users/managers to submit asset disposal requests.
    
    Security:
    - All users can request disposal for assets they manage
    - Admins can dispose directly (no approval needed)
    - Company-scoped
    - Branch validation
    
    URL: /assets/<uuid>/request-disposal/
    Template: assets/asset_disposal_request_form.html
    """
    model = ApprovalRequest
    template_name = 'assets/asset_disposal_request_form.html'
    fields = []  # We'll use custom form handling
    
    def dispatch(self, request, *args, **kwargs):
        """Check permissions and get asset."""
        user = request.user
        asset_uuid = kwargs.get('asset_uuid')
        
        # Get asset
        company = getattr(request, 'company', None)
        try:
            self.asset = Asset.objects.get(
                uuid=asset_uuid,
                company=company
            )
        except Asset.DoesNotExist:
            messages.error(request, "Asset not found.")
            return redirect('asset_list')
        
        # Check if asset is already disposed
        if self.asset.status in [Asset.STATUS_RETIRED, Asset.STATUS_DELETED, Asset.STATUS_LOST]:
            messages.warning(request, f"Asset is already {self.asset.get_status_display()}.")
            return redirect('asset_detail_by_uuid', uuid=asset_uuid)
        
        # Admins can dispose directly (skip approval)
        if user.role == 'admin' and request.GET.get('from') != 'delete':
            messages.info(request, "As an admin, you can change asset status directly from the edit page.")

            # Prefer namespaced assets edit route; fall back to legacy/global naming if needed.
            try:
                return redirect('assets:asset_update', uuid=asset_uuid)
            except Exception:
                try:
                    return redirect('asset_update', uuid=asset_uuid)
                except Exception:
                    return redirect('asset_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Prepare form context."""
        context = super().get_context_data(**kwargs)
        context['asset'] = self.asset
        context['priority_choices'] = ApprovalRequest.PRIORITY_CHOICES
        
        # Disposal method choices
        context['disposal_methods'] = [
            ('retired', 'Retired - Asset reached end of life'),
            ('lost', 'Lost - Asset cannot be located'),
            ('deleted', 'Deleted - Asset permanently removed'),
        ]
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle asset disposal request submission."""
        company = getattr(request, 'company', None)
        user = request.user
        
        try:
            with transaction.atomic():
                # Extract form data
                title = request.POST.get('title', '').strip()
                reason = request.POST.get('reason', '').strip()
                disposal_method = request.POST.get('disposal_method', 'retired')
                priority = request.POST.get('priority', ApprovalRequest.PRIORITY_MEDIUM)
                
                # Validate required fields
                if not all([title, reason]):
                    messages.error(request, "Please fill in all required fields.")
                    return self.get(request, *args, **kwargs)
                
                # Validate disposal method
                valid_methods = ['retired', 'lost', 'deleted']
                if disposal_method not in valid_methods:
                    messages.error(request, "Invalid disposal method selected.")
                    return self.get(request, *args, **kwargs)
                
                # Create approval request
                approval_request = ApprovalRequest.objects.create(
                    company=company,
                    branch=self.asset.branch or Branch.objects.filter(company=company, is_active=True).first(),
                    request_type=ApprovalRequest.TYPE_ASSET_DISPOSAL,
                    title=title,
                    description=reason,
                    requested_by=user,
                    priority=priority,
                    metadata={
                        'asset_id': self.asset.id,
                        'asset_uuid': str(self.asset.uuid),
                        'asset_description': str(self.asset),
                        'disposal_reason': reason,
                        'disposal_method': disposal_method,
                        'current_status': self.asset.status,
                    }
                )
                
                # Auto-assign to admin
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admin = User.objects.filter(
                    company=company,
                    role='admin',
                    is_active=True
                ).first()
                
                if admin:
                    approval_request.assigned_to = admin
                    approval_request.save()
                    
                    # Create notification for admin
                    from tenancy.models import Alert
                    Alert.objects.create(
                        company=company,
                        branch=approval_request.branch,
                        recipient=admin,
                        level=Alert.LEVEL_WARNING,
                        message=f"Asset disposal request from {user.get_full_name() or user.username}: {title}",
                        context={
                            'request_id': approval_request.pk,
                            'request_type': 'asset_disposal',
                            'requested_by': user.pk,
                            'asset_id': self.asset.id,
                            'asset_uuid': str(self.asset.uuid),
                        }
                    )
                
                # Log audit event
                log_audit(
                    user,
                    "asset_disposal_requested",
                    self.asset,
                    f"Requested asset disposal: {title}. Reason: {reason}",
                    company=company,
                    branch=self.asset.branch,
                    metadata={
                        'request_id': approval_request.pk,
                        'disposal_method': disposal_method,
                        'priority': priority,
                    }
                )
                
                messages.success(
                    request,
                    f"Asset disposal request '{title}' submitted successfully. "
                    f"Assigned to admin for review."
                )
                
                return redirect('approval_dashboard')
        
        except Exception as e:
            messages.error(request, f"Failed to submit request: {str(e)}")
            return self.get(request, *args, **kwargs)


@login_required
@require_http_methods(["GET"])
def api_pending_disposal_requests(request):
    """
    API endpoint to fetch pending asset disposal requests.
    
    Security:
    - Only admins can access
    - Company-scoped
    
    Returns:
        JSON with pending requests list
    """
    company = getattr(request, 'company', None)
    if not company:
        return JsonResponse({'success': False, 'error': 'Company context required.'}, status=403)
    
    user = request.user
    user_role = getattr(user, 'role', 'user')
    
    # Only admins can view disposal requests
    if user_role != 'admin':
        return JsonResponse({
            'success': False,
            'error': 'Only admins can view asset disposal requests.'
        }, status=403)
    
    # Build queryset
    queryset = ApprovalRequest.objects.filter(
        company=company,
        request_type=ApprovalRequest.TYPE_ASSET_DISPOSAL,
        status=ApprovalRequest.STATUS_PENDING
    ).select_related(
        'requested_by',
        'branch',
        'assigned_to'
    ).order_by('-created_at')
    
    # Serialize data
    requests_data = []
    for req in queryset:
        asset_uuid = req.metadata.get('asset_uuid')
        requests_data.append({
            'id': req.pk,
            'title': req.title,
            'description': req.description,
            'asset_description': req.metadata.get('asset_description', 'N/A'),
            'asset_uuid': asset_uuid,
            'disposal_method': req.metadata.get('disposal_method', 'retired'),
            'priority': req.get_priority_display(),
            'requested_by': req.requested_by.get_full_name() or req.requested_by.username,
            'requested_at': req.created_at.isoformat(),
            'branch': req.branch.name if req.branch else 'N/A',
        })
    
    return JsonResponse({
        'success': True,
        'requests': requests_data,
        'count': len(requests_data)
    })
