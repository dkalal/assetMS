"""
Asset Creation Request Views

Provides secure workflow for managers to request asset creation
with admin approval before actual asset registration.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, ListView

from assets.forms import AssetForm
from assets.models import Asset, AssetCategory, AssetCategoryField
from audit.utils import log_audit
from tenancy.approval_models import ApprovalRequest
from tenancy.mixins import BranchContextMixin
from tenancy.models import Branch
from users.utils import can


class AssetCreationRequestView(LoginRequiredMixin, BranchContextMixin, CreateView):
    """
    View for managers to submit asset creation requests.
    
    Security:
    - Only managers and admins can access
    - Managers submit requests, admins can create directly
    - Company-scoped
    - Branch validation
    
    URL: /assets/request-creation/
    Template: assets/asset_creation_request_form.html
    """
    model = ApprovalRequest
    template_name = 'assets/asset_creation_request_form.html'
    fields = []  # We'll use custom form handling
    
    def dispatch(self, request, *args, **kwargs):
        """Check permissions before processing."""
        user = request.user
        
        # Check if user has permission to request asset creation
        if not can(user, 'request_asset_creation') and not can(user, 'create_assets'):
            messages.error(request, "You do not have permission to request asset creation.")
            return redirect('asset_list')
        
        # If admin with direct creation permission, redirect to direct creation
        if can(user, 'create_assets') and user.role == 'admin':
            messages.info(request, "As an admin, you can create assets directly.")
            return redirect('asset_register')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Prepare form context."""
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, 'company', None)
        user = self.request.user
        
        # Get categories for dropdown
        context['categories'] = AssetCategory.objects.for_company(company).order_by('name')
        
        # Get branches for dropdown
        context['branches'] = Branch.objects.filter(
            company=company,
            is_active=True
        ).order_by('name')
        
        # Get user's primary branch
        context['user_branch'] = getattr(user, 'primary_branch', None)
        
        # Priority choices
        context['priority_choices'] = ApprovalRequest.PRIORITY_CHOICES
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle asset creation request submission."""
        company = getattr(request, 'company', None)
        user = request.user
        
        try:
            with transaction.atomic():
                # Extract form data
                category_id = request.POST.get('category_id')
                branch_id = request.POST.get('branch_id')
                title = request.POST.get('title', '').strip()
                description = request.POST.get('description', '').strip()
                justification = request.POST.get('justification', '').strip()
                priority = request.POST.get('priority', ApprovalRequest.PRIORITY_MEDIUM)
                
                # Validate required fields
                if not all([category_id, branch_id, title, justification]):
                    messages.error(request, "Please fill in all required fields.")
                    return self.get(request, *args, **kwargs)
                
                # Validate category
                try:
                    category = AssetCategory.objects.for_company(company).get(pk=category_id)
                except AssetCategory.DoesNotExist:
                    messages.error(request, "Invalid category selected.")
                    return self.get(request, *args, **kwargs)
                
                # Validate branch
                try:
                    branch = Branch.objects.get(pk=branch_id, company=company, is_active=True)
                except Branch.DoesNotExist:
                    messages.error(request, "Invalid branch selected.")
                    return self.get(request, *args, **kwargs)
                
                # Build asset data from dynamic fields
                asset_data = {
                    'category_id': int(category_id),
                    'branch_id': int(branch_id),
                    'description': description,
                    'status': request.POST.get('status', Asset.STATUS_ACTIVE),
                    'dynamic_data': {},
                }
                
                # Extract dynamic fields based on category
                fields = AssetCategoryField.objects.for_company(company).filter(category=category)
                for field in fields:
                    field_value = request.POST.get(f'field_{field.key}', '').strip()
                    if field_value:
                        asset_data['dynamic_data'][field.key] = field_value
                    elif field.required:
                        messages.error(request, f"Required field '{field.label}' is missing.")
                        return self.get(request, *args, **kwargs)
                
                # Check for assigned_to
                assigned_to_id = request.POST.get('assigned_to_id')
                if assigned_to_id:
                    asset_data['assigned_to_id'] = int(assigned_to_id)
                
                # Create approval request
                approval_request = ApprovalRequest.objects.create(
                    company=company,
                    branch=branch,
                    request_type=ApprovalRequest.TYPE_ASSET_CREATION,
                    title=title,
                    description=f"{description}\n\nJustification: {justification}",
                    requested_by=user,
                    priority=priority,
                    metadata={
                        'asset_data': asset_data,
                        'justification': justification,
                        'category_name': category.name,
                    }
                )
                
                # Auto-assign to branch manager or admin
                if branch.manager:
                    approval_request.assigned_to = branch.manager
                else:
                    # Assign to first available admin
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
                
                # Create notification for assigned user
                if approval_request.assigned_to:
                    from tenancy.models import Alert
                    Alert.objects.create(
                        company=company,
                        branch=branch,
                        recipient=approval_request.assigned_to,
                        level=Alert.LEVEL_INFO,
                        message=f"New asset creation request from {user.get_full_name() or user.username}: {title}",
                        context={
                            'request_id': approval_request.pk,
                            'request_type': 'asset_creation',
                            'requested_by': user.pk,
                        }
                    )
                
                # Log audit event
                log_audit(
                    user,
                    "asset_creation_requested",
                    details=f"Requested asset creation: {title}",
                    company=company,
                    branch=branch,
                    metadata={
                        'request_id': approval_request.pk,
                        'category': category.name,
                        'priority': priority,
                    }
                )
                
                messages.success(
                    request,
                    f"Asset creation request '{title}' submitted successfully. "
                    f"Assigned to {approval_request.assigned_to.get_full_name() if approval_request.assigned_to else 'admin'} for review."
                )
                
                return redirect('approval_dashboard')
        
        except Exception as e:
            messages.error(request, f"Failed to submit request: {str(e)}")
            return self.get(request, *args, **kwargs)


@login_required
@require_http_methods(["GET"])
def api_pending_asset_creation_requests(request):
    """
    API endpoint to fetch pending asset creation requests.
    
    Security:
    - Only admins and managers can access
    - Company-scoped
    - Branch-filtered for managers
    
    Returns:
        JSON with pending requests list
    """
    company = getattr(request, 'company', None)
    if not company:
        return JsonResponse({'success': False, 'error': 'Company context required.'}, status=403)
    
    user = request.user
    user_role = getattr(user, 'role', 'user')
    
    # WORLD-CLASS: Explicit role-based access control
    if user_role not in ['admin', 'manager']:
        return JsonResponse({
            'success': False,
            'error': 'Only admins and managers can view asset creation requests.'
        }, status=403)
    
    # Build queryset
    queryset = ApprovalRequest.objects.filter(
        company=company,
        request_type=ApprovalRequest.TYPE_ASSET_CREATION,
        status=ApprovalRequest.STATUS_PENDING
    ).select_related('branch', 'requested_by', 'assigned_to')
    
    # Filter by branch for managers
    if user_role == 'manager':
        managed_branches = Branch.objects.filter(manager=user, company=company)
        queryset = queryset.filter(branch__in=managed_branches)
    
    # Serialize requests
    requests_data = []
    for req in queryset.order_by('-created_at'):
        asset_data = req.metadata.get('asset_data', {})
        requests_data.append({
            'id': req.pk,
            'title': req.title,
            'description': req.description,
            'requested_by': {
                'id': req.requested_by.pk,
                'name': req.requested_by.get_full_name() or req.requested_by.username,
            },
            'branch': {
                'id': req.branch.pk,
                'name': req.branch.name,
            },
            'priority': req.priority,
            'priority_display': req.get_priority_display(),
            'created_at': req.created_at.isoformat(),
            'is_overdue': req.is_overdue,
            'asset_preview': {
                'category_name': req.metadata.get('category_name', 'N/A'),
                'name': asset_data.get('dynamic_data', {}).get('name', 'N/A'),
                'model': asset_data.get('dynamic_data', {}).get('model', 'N/A'),
            }
        })
    
    return JsonResponse({
        'success': True,
        'requests': requests_data,
        'total': len(requests_data),
        'pending_count': len(requests_data),
    })


@login_required
@require_http_methods(["POST"])
def api_quick_approve_asset_creation(request, request_id):
    """
    Quick approve asset creation request via API.
    
    Security:
    - Only admins and assigned managers can approve
    - Company-scoped
    - Atomic transaction
    
    Returns:
        JSON with success status and created asset info
    """
    company = getattr(request, 'company', None)
    if not company:
        return JsonResponse({'success': False, 'error': 'Company context required.'}, status=403)
    
    user = request.user
    user_role = getattr(user, 'role', 'user')
    
    # WORLD-CLASS: Explicit role-based access control
    if user_role not in ['admin', 'manager']:
        return JsonResponse({
            'success': False,
            'error': 'Only admins and managers can approve asset creation requests.'
        }, status=403)
    
    try:
        approval_request = ApprovalRequest.objects.get(
            pk=request_id,
            company=company,
            request_type=ApprovalRequest.TYPE_ASSET_CREATION
        )
    except ApprovalRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Request not found.'}, status=404)
    
    # Verify user can approve this request
    can_approve = (
        user.role == 'admin' or
        approval_request.assigned_to == user or
        (user.role == 'manager' and approval_request.branch.manager == user)
    )
    
    if not can_approve:
        return JsonResponse({'success': False, 'error': 'You cannot approve this request.'}, status=403)
    
    try:
        with transaction.atomic():
            # Approve request
            notes = request.POST.get('notes', 'Quick approved via API')
            approval_request.approve(approved_by=user, notes=notes)
            
            # Create asset
            asset = approval_request.create_asset_from_approval()
            
            return JsonResponse({
                'success': True,
                'message': f"Request approved and asset created successfully.",
                'asset': {
                    'id': asset.id,
                    'uuid': str(asset.uuid),
                    'description': asset.description,
                },
                'request_id': approval_request.pk,
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f"Approval failed: {str(e)}"
        }, status=500)
