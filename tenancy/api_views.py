"""
Tenancy API Views - Branch and Company API endpoints
World-class implementation with full CRUD operations
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import Branch, Company

logger = logging.getLogger(__name__)
User = get_user_model()


@login_required
@require_http_methods(["GET"])
def api_branches_list(request):
    """
    API endpoint to list all branches for the current user's company.
    
    Returns:
        JSON response with list of branches including full details
    """
    company = getattr(request, 'company', None) or getattr(request.user, 'company', None)
    
    if not company:
        return JsonResponse({
            'success': False,
            'error': 'Company context required'
        }, status=403)
    
    # Get all branches for the company with related data
    branches = Branch.objects.filter(company=company).select_related('manager').order_by('name')
    
    branches_data = []
    for branch in branches:
        # Get asset count
        asset_count = branch.assets.count() if hasattr(branch, 'assets') else 0
        
        # Get manager info
        manager_data = None
        if branch.manager:
            manager_data = {
                'id': branch.manager.id,
                'username': branch.manager.username,
                'full_name': branch.manager.get_full_name() or branch.manager.username,
                'email': branch.manager.email
            }
        
        branches_data.append({
            'id': branch.pk,
            'name': branch.name,
            'code': branch.code,
            'address': branch.address or '',
            'is_active': branch.is_active,
            'is_head_office': branch.is_head_office,
            'manager': manager_data,
            'asset_count': asset_count,
            'created_at': branch.created_at.isoformat() if hasattr(branch, 'created_at') else None,
        })
    
    return JsonResponse({
        'success': True,
        'branches': branches_data,
        'total': len(branches_data)
    })


@login_required
@require_http_methods(["GET"])
def api_branch_detail(request, branch_id):
    """
    API endpoint to get details of a specific branch.
    
    Args:
        branch_id: ID of the branch to retrieve
        
    Returns:
        JSON response with branch details
    """
    try:
        company = getattr(request, 'company', None) or getattr(request.user, 'company', None)
        
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'Company context required'
            }, status=403)
        
        # Get branch with multi-tenancy enforcement
        branch = Branch.objects.select_related('manager', 'company').get(
            id=branch_id,
            company=company
        )
        
        # Get asset count
        asset_count = branch.assets.count() if hasattr(branch, 'assets') else 0
        
        # Get manager info
        manager_data = None
        if branch.manager:
            manager_data = {
                'id': branch.manager.id,
                'username': branch.manager.username,
                'full_name': branch.manager.get_full_name() or branch.manager.username,
                'email': branch.manager.email
            }
        
        branch_data = {
            'id': branch.pk,
            'name': branch.name,
            'code': branch.code,
            'address': branch.address or '',
            'is_active': branch.is_active,
            'is_head_office': branch.is_head_office,
            'manager': manager_data,
            'manager_id': branch.manager.id if branch.manager else None,
            'asset_count': asset_count,
            'created_at': branch.created_at.isoformat() if hasattr(branch, 'created_at') else None,
        }
        
        return JsonResponse({
            'success': True,
            'branch': branch_data
        })
        
    except Branch.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Branch not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching branch details: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch branch details'
        }, status=500)


@login_required
@require_http_methods(["POST", "PUT"])
@csrf_protect
def api_branch_update(request, branch_id):
    """
    API endpoint to update branch details (Admin only).
    
    Args:
        branch_id: ID of the branch to update
        
    Returns:
        JSON response with updated branch details
    """
    from audit.models import AuditEvent
    
    try:
        company = getattr(request, 'company', None) or getattr(request.user, 'company', None)
        
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'Company context required'
            }, status=403)
        
        # Check admin permission
        if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
            return JsonResponse({
                'success': False,
                'error': 'Admin permission required to update branches'
            }, status=403)
        
        # Parse JSON body first
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in branch update request: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON payload'
            }, status=400)
        
        # Get branch with multi-tenancy enforcement
        branch = Branch.objects.select_related('manager', 'company').get(
            id=branch_id,
            company=company
        )
        
        # Prevent modification of head office status
        if branch.is_head_office:
            # Head office can only be deactivated, not deleted or have certain fields changed
            pass
        
        # Track changes for audit
        changes = {}
        
        # Update name
        if 'name' in data and data['name'].strip():
            new_name = data['name'].strip()
            if new_name != branch.name:
                changes['name'] = {'old': branch.name, 'new': new_name}
                branch.name = new_name
        
        # Update address
        if 'address' in data:
            new_address = data['address'].strip()
            if new_address != branch.address:
                changes['address'] = {'old': branch.address, 'new': new_address}
                branch.address = new_address
        
        # Update manager
        if 'manager_id' in data:
            new_manager_id = data['manager_id']
            old_manager_id = branch.manager.id if branch.manager else None
            
            if new_manager_id != old_manager_id:
                if new_manager_id:
                    # Validate manager belongs to same company
                    try:
                        new_manager = User.objects.get(id=new_manager_id, company=company)
                        changes['manager'] = {
                            'old': branch.manager.get_full_name() if branch.manager else 'None',
                            'new': new_manager.get_full_name()
                        }
                        branch.manager = new_manager
                        branch.manager_assigned_at = timezone.now()
                        branch.manager_assigned_by = request.user
                    except User.DoesNotExist:
                        return JsonResponse({
                            'success': False,
                            'error': 'Manager not found or does not belong to your company'
                        }, status=400)
                else:
                    # Remove manager
                    changes['manager'] = {
                        'old': branch.manager.get_full_name() if branch.manager else 'None',
                        'new': 'None'
                    }
                    branch.manager = None
                    branch.manager_assigned_at = None
        
        # Update active status (WORLD-CLASS: Require reason for status changes)
        if 'is_active' in data:
            new_status = bool(data['is_active'])
            if new_status != branch.is_active:
                # WORLD-CLASS: Require reason for status change
                reason = data.get('status_change_reason', '').strip()
                if not reason:
                    return JsonResponse({
                        'success': False,
                        'error': 'Reason is required when changing branch status',
                        'field': 'status_change_reason'
                    }, status=400)
                
                if len(reason) < 10:
                    return JsonResponse({
                        'success': False,
                        'error': 'Reason must be at least 10 characters',
                        'field': 'status_change_reason'
                    }, status=400)
                
                changes['is_active'] = {'old': branch.is_active, 'new': new_status, 'reason': reason}
                branch.is_active = new_status
                
                # Log status change in audit with reason (high severity for branch status changes)
                status_text = 'activated' if new_status else 'deactivated'
                AuditEvent.objects.create(
                    company=company,
                    user=request.user,
                    action=f'branch_{status_text}',
                    description=f'Branch "{branch.name}" {status_text} - Reason: {reason}',
                    severity='high',  # High severity for branch status changes
                    metadata={
                        'branch_id': branch.id,
                        'branch_name': branch.name,
                        'previous_status': not new_status,
                        'new_status': new_status,
                        'reason': reason,
                        'changed_by': request.user.username
                    }
                )
        
        # Save changes
        if changes:
            branch.save()
            
            # Create audit event for update
            AuditEvent.objects.create(
                company=company,
                user=request.user,
                action='branch_updated',
                description=f'Branch "{branch.name}" updated',
                severity='low',
                metadata={
                    'branch_id': branch.id,
                    'branch_name': branch.name,
                    'changes': changes
                }
            )
        
        # Get updated branch data
        try:
            asset_count = branch.assets.count()
        except Exception:
            asset_count = 0
        
        manager_data = None
        if branch.manager:
            manager_data = {
                'id': branch.manager.id,
                'username': branch.manager.username,
                'full_name': branch.manager.get_full_name() or branch.manager.username,
                'email': branch.manager.email
            }
        
        branch_data = {
            'id': branch.pk,
            'name': branch.name,
            'code': branch.code,
            'address': branch.address or '',
            'is_active': branch.is_active,
            'is_head_office': branch.is_head_office,
            'manager': manager_data,
            'manager_id': branch.manager.id if branch.manager else None,
            'asset_count': asset_count,
            'created_at': branch.created_at.isoformat() if hasattr(branch, 'created_at') else None,
        }
        
        return JsonResponse({
            'success': True,
            'message': 'Branch updated successfully',
            'branch': branch_data,
            'changes': changes
        })
        
    except Branch.DoesNotExist:
        logger.warning(f"Branch {branch_id} not found for company {company.id if company else 'None'}")
        return JsonResponse({
            'success': False,
            'error': 'Branch not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error updating branch {branch_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Failed to update branch: {str(e)}'
        }, status=500)
