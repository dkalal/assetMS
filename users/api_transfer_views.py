# users/api_transfer_views.py
"""
User Branch Transfer API Endpoints

WORLD-CLASS: RESTful API for hybrid user branch transfer workflow.

Endpoints:
1. POST /users/api/transfer/initiate/ - Initiate transfer
2. GET /users/api/transfer/<id>/ - Get transfer details
3. POST /users/api/transfer/<id>/submit-selections/ - User submits selections
4. POST /users/api/transfer/<id>/approve/ - Admin approves
5. POST /users/api/transfer/<id>/reject/ - Admin rejects
6. POST /users/api/transfer/<id>/cancel/ - Cancel transfer
7. GET /users/api/transfer/pending/ - Get pending transfers

Security:
- Multi-tenancy enforcement
- Role-based permissions
- CSRF protection
- Input validation

Architecture:
- RESTful design
- JSON responses
- Comprehensive error handling
- Complete audit trail
"""

import json
import logging
from typing import Dict, Any

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from tenancy.models import Branch
from users.models_transfer import UserBranchTransferRequest, AssetTransferSelection
from users.services.branch_transfer_service import UserBranchTransferService

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def serialize_transfer_request(transfer_request: UserBranchTransferRequest) -> Dict[str, Any]:
    """
    Serialize transfer request for API response.
    
    Returns comprehensive transfer data including statistics and relationships.
    """
    return {
        'id': transfer_request.id,
        'user': {
            'id': transfer_request.user.id,
            'username': transfer_request.user.username,
            'full_name': transfer_request.user.get_full_name() or transfer_request.user.username,
            'email': transfer_request.user.email,
        },
        'from_branch': {
            'id': transfer_request.from_branch.id,
            'name': transfer_request.from_branch.name,
        } if transfer_request.from_branch else None,
        'to_branch': {
            'id': transfer_request.to_branch.id,
            'name': transfer_request.to_branch.name,
        },
        'status': transfer_request.status,
        'status_display': transfer_request.get_status_display(),
        'initiation_reason': transfer_request.initiation_reason,
        'user_selection_notes': transfer_request.user_selection_notes,
        'approval_reason': transfer_request.approval_reason,
        'rejection_reason': transfer_request.rejection_reason,
        'initiated_by': {
            'id': transfer_request.initiated_by.id,
            'username': transfer_request.initiated_by.username,
            'full_name': transfer_request.initiated_by.get_full_name() or transfer_request.initiated_by.username,
        } if transfer_request.initiated_by else None,
        'approved_by': {
            'id': transfer_request.approved_by.id,
            'username': transfer_request.approved_by.username,
            'full_name': transfer_request.approved_by.get_full_name() or transfer_request.approved_by.username,
        } if transfer_request.approved_by else None,
        'timestamps': {
            'initiated_at': transfer_request.initiated_at.isoformat() if transfer_request.initiated_at else None,
            'user_selection_at': transfer_request.user_selection_at.isoformat() if transfer_request.user_selection_at else None,
            'approval_decision_at': transfer_request.approval_decision_at.isoformat() if transfer_request.approval_decision_at else None,
            'completed_at': transfer_request.completed_at.isoformat() if transfer_request.completed_at else None,
        },
        'statistics': {
            'total_assets': transfer_request.total_assets,
            'selected_by_user': transfer_request.assets_selected_by_user,
            'approved': transfer_request.assets_approved,
            'transferred': transfer_request.assets_transferred,
            'unassigned': transfer_request.assets_unassigned,
        },
        'can_user_select': transfer_request.can_user_select_assets,
        'can_be_approved': transfer_request.can_be_approved,
        'can_be_executed': transfer_request.can_be_executed,
        'is_active': transfer_request.is_active,
        'is_final': transfer_request.is_final,
    }


def serialize_asset_selection(selection: AssetTransferSelection) -> Dict[str, Any]:
    """Serialize asset selection for API response"""
    asset = selection.asset
    
    # Build asset identifier (Asset model has no 'name' field)
    asset_identifier = asset.serial_number or asset.asset_tag or f"Asset #{asset.id}"
    
    return {
        'id': selection.id,
        'asset': {
            'id': asset.id,
            'uuid': str(asset.uuid),
            'identifier': asset_identifier,
            'category': asset.category.name,
            'status': asset.status,
            'status_display': asset.get_status_display(),
            'branch': {
                'id': asset.branch.id,
                'name': asset.branch.name,
            } if asset.branch else None,
            'serial_number': getattr(asset, 'serial_number', None),
            'asset_tag': getattr(asset, 'asset_tag', None),
            'estimated_value': float(getattr(asset, 'purchase_price', 0) or 0),
        },
        'selected_by_user': selection.selected_by_user,
        'user_selection_reason': selection.user_selection_reason,
        'user_selected_at': selection.user_selected_at.isoformat() if selection.user_selected_at else None,
        'approved_by_admin': selection.approved_by_admin,
        'admin_decision_reason': selection.admin_decision_reason,
        'admin_decision_at': selection.admin_decision_at.isoformat() if selection.admin_decision_at else None,
        'status': selection.status,
        'status_display': selection.get_status_display(),
        'executed_at': selection.executed_at.isoformat() if selection.executed_at else None,
        'execution_error': selection.execution_error,
    }


# ============================================================================
# API ENDPOINTS
# ============================================================================

@csrf_protect
@login_required
@require_http_methods(["POST"])
def api_initiate_transfer(request):
    """
    API: Initiate user branch transfer.
    
    POST /users/api/transfer/initiate/
    
    Payload:
    {
        "user_id": 123,
        "to_branch_id": 456,
        "reason": "Employee relocation to London office",
        "effective_date": "2024-12-15" (optional),
        "metadata": {} (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Transfer request created",
        "data": {
            "transfer_request_id": 789,
            ...
        }
    }
    
    Permissions: Admin or Manager only
    """
    
    try:
        # Parse request
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
        
        user_id = data.get('user_id')
        to_branch_id = data.get('to_branch_id')
        reason = data.get('reason', '').strip()
        effective_date = data.get('effective_date')
        metadata = data.get('metadata', {})
        
        # Validate inputs
        if not user_id or not to_branch_id or not reason:
            return JsonResponse({
                'success': False,
                'error': 'user_id, to_branch_id, and reason are required'
            }, status=400)
        
        # Get objects
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'User must belong to a company'
            }, status=403)
        
        try:
            user = User.objects.get(id=user_id, company=company)
            to_branch = Branch.objects.get(id=to_branch_id, company=company)
        except (User.DoesNotExist, Branch.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'User or branch not found'
            }, status=404)
        
        # Initiate transfer
        result = UserBranchTransferService.initiate_transfer(
            user=user,
            to_branch=to_branch,
            initiated_by=request.user,
            reason=reason,
            effective_date=effective_date,
            metadata=metadata
        )
        
        if result.success:
            return JsonResponse({
                'success': True,
                'message': result.message,
                'data': result.data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.message,
                'errors': result.errors
            }, status=400)
    
    except Exception as e:
        logger.error(f'Transfer initiation error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to initiate transfer',
            'details': str(e)
        }, status=500)


@csrf_protect
@login_required
@require_http_methods(["GET"])
def api_get_transfer(request, transfer_id):
    """
    API: Get transfer request details with asset selections.
    
    GET /users/api/transfer/<id>/
    
    Response includes complete transfer data and all asset selections.
    """
    
    try:
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'User must belong to a company'
            }, status=403)
        
        # Get transfer request
        transfer_request = UserBranchTransferRequest.objects.select_related(
            'user',
            'from_branch',
            'to_branch',
            'initiated_by',
            'approved_by'
        ).prefetch_related(
            Prefetch(
                'asset_selections',
                queryset=AssetTransferSelection.objects.select_related(
                    'asset',
                    'asset__category',
                    'asset__branch'
                ).order_by('asset__category__name', 'asset__name')
            )
        ).get(id=transfer_id, company=company)
        
        # Permission check: Only user, admin, or involved parties can view
        if not (
            request.user.is_superuser or
            request.user == transfer_request.user or
            request.user == transfer_request.initiated_by or
            request.user == transfer_request.approved_by
        ):
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        # Serialize data
        transfer_data = serialize_transfer_request(transfer_request)
        
        # Add asset selections
        transfer_data['asset_selections'] = [
            serialize_asset_selection(selection)
            for selection in transfer_request.asset_selections.all()
        ]
        
        return JsonResponse({
            'success': True,
            'data': transfer_data
        })
    
    except UserBranchTransferRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Transfer request not found'
        }, status=404)
    except Exception as e:
        logger.error(f'Get transfer error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to retrieve transfer',
            'details': str(e)
        }, status=500)


@csrf_protect
@login_required
@require_http_methods(["POST"])
def api_submit_selections(request, transfer_id):
    """
    API: User submits asset selections.
    
    POST /users/api/transfer/<id>/submit-selections/
    
    Payload:
    {
        "selected_asset_ids": [1, 2, 3],
        "selection_reasons": {
            "1": "Primary work laptop",
            "2": "Company phone"
        },
        "notes": "Optional overall notes"
    }
    
    Response:
    {
        "success": true,
        "message": "Selections submitted",
        "data": {
            "selected_count": 2,
            "not_selected_count": 3
        }
    }
    """
    
    try:
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'User must belong to a company'
            }, status=403)
        
        # Get transfer request
        transfer_request = UserBranchTransferRequest.objects.get(
            id=transfer_id,
            company=company
        )
        
        # Permission check: Only the user being transferred can submit selections
        if request.user != transfer_request.user:
            return JsonResponse({
                'success': False,
                'error': 'Only the user being transferred can submit selections'
            }, status=403)
        
        # Parse request
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
        
        selected_asset_ids = data.get('selected_asset_ids', [])
        selection_reasons_str = data.get('selection_reasons', {})
        notes = data.get('notes', '').strip()
        
        # Convert selection_reasons keys to integers
        selection_reasons = {int(k): v for k, v in selection_reasons_str.items()}
        
        # Submit selections
        result = UserBranchTransferService.submit_asset_selections(
            transfer_request=transfer_request,
            selected_asset_ids=selected_asset_ids,
            selection_reasons=selection_reasons,
            notes=notes
        )
        
        if result.success:
            return JsonResponse({
                'success': True,
                'message': result.message,
                'data': result.data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.message,
                'errors': result.errors
            }, status=400)
    
    except UserBranchTransferRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Transfer request not found'
        }, status=404)
    except Exception as e:
        logger.error(f'Submit selections error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to submit selections',
            'details': str(e)
        }, status=500)


@csrf_protect
@login_required
@require_http_methods(["POST"])
def api_approve_transfer(request, transfer_id):
    """
    API: Admin/Manager approves transfer.
    
    POST /users/api/transfer/<id>/approve/
    
    Payload:
    {
        "approval_reason": "Approved for employee relocation",
        "approved_asset_ids": [1, 2] (optional - if null, approves all),
        "auto_execute": true (optional - default true)
    }
    """
    
    try:
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'User must belong to a company'
            }, status=403)
        
        # Get transfer request
        transfer_request = UserBranchTransferRequest.objects.get(
            id=transfer_id,
            company=company
        )
        
        # Parse request
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
        
        approval_reason = data.get('approval_reason', '').strip()
        approved_asset_ids = data.get('approved_asset_ids')
        auto_execute = data.get('auto_execute', True)
        
        # Approve transfer
        result = UserBranchTransferService.approve_transfer(
            transfer_request=transfer_request,
            approved_by=request.user,
            approval_reason=approval_reason,
            approved_asset_ids=approved_asset_ids,
            auto_execute=auto_execute
        )
        
        if result.success:
            return JsonResponse({
                'success': True,
                'message': result.message,
                'data': result.data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.message,
                'errors': result.errors
            }, status=400)
    
    except UserBranchTransferRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Transfer request not found'
        }, status=404)
    except Exception as e:
        logger.error(f'Approve transfer error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to approve transfer',
            'details': str(e)
        }, status=500)


@csrf_protect
@login_required
@require_http_methods(["POST"])
def api_reject_transfer(request, transfer_id):
    """
    API: Admin/Manager rejects transfer.
    
    POST /users/api/transfer/<id>/reject/
    
    Payload:
    {
        "rejection_reason": "Reason for rejection"
    }
    """
    
    try:
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'User must belong to a company'
            }, status=403)
        
        # Get transfer request
        transfer_request = UserBranchTransferRequest.objects.get(
            id=transfer_id,
            company=company
        )
        
        # Parse request
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
        
        rejection_reason = data.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            return JsonResponse({
                'success': False,
                'error': 'Rejection reason is required'
            }, status=400)
        
        # Reject transfer
        result = UserBranchTransferService.reject_transfer(
            transfer_request=transfer_request,
            rejected_by=request.user,
            rejection_reason=rejection_reason
        )
        
        if result.success:
            return JsonResponse({
                'success': True,
                'message': result.message,
                'data': result.data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.message,
                'errors': result.errors
            }, status=400)
    
    except UserBranchTransferRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Transfer request not found'
        }, status=404)
    except Exception as e:
        logger.error(f'Reject transfer error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to reject transfer',
            'details': str(e)
        }, status=500)


@csrf_protect
@login_required
@require_http_methods(["POST"])
def api_cancel_transfer(request, transfer_id):
    """
    API: Cancel transfer request.
    
    POST /users/api/transfer/<id>/cancel/
    
    Payload:
    {
        "cancellation_reason": "Reason for cancellation"
    }
    """
    
    try:
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'User must belong to a company'
            }, status=403)
        
        # Get transfer request
        transfer_request = UserBranchTransferRequest.objects.get(
            id=transfer_id,
            company=company
        )
        
        # Parse request
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
        
        cancellation_reason = data.get('cancellation_reason', '').strip()
        
        if not cancellation_reason:
            return JsonResponse({
                'success': False,
                'error': 'Cancellation reason is required'
            }, status=400)
        
        # Cancel transfer
        result = UserBranchTransferService.cancel_transfer(
            transfer_request=transfer_request,
            cancelled_by=request.user,
            cancellation_reason=cancellation_reason
        )
        
        if result.success:
            return JsonResponse({
                'success': True,
                'message': result.message,
                'data': result.data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.message,
                'errors': result.errors
            }, status=400)
    
    except UserBranchTransferRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Transfer request not found'
        }, status=404)
    except Exception as e:
        logger.error(f'Cancel transfer error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to cancel transfer',
            'details': str(e)
        }, status=500)


@csrf_protect
@login_required
@require_http_methods(["GET"])
def api_get_pending_transfers(request):
    """
    API: Get pending transfers for current user.
    
    GET /users/api/transfer/pending/
    
    Returns:
    - Transfers pending user selection (if user is being transferred)
    - Transfers pending approval (if user is admin/manager)
    
    Response:
    {
        "success": true,
        "data": {
            "pending_selection": [...],
            "pending_approval": [...]
        }
    }
    """
    
    try:
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'User must belong to a company'
            }, status=403)
        
        # Get transfers pending user selection (for current user)
        pending_selection = UserBranchTransferRequest.objects.filter(
            company=company,
            user=request.user,
            status=UserBranchTransferRequest.STATUS_PENDING_USER_SELECTION
        ).select_related(
            'from_branch',
            'to_branch',
            'initiated_by'
        )
        
        # Get transfers pending approval (if admin/manager)
        pending_approval = []
        if request.user.is_staff or request.user.is_superuser:
            pending_approval = UserBranchTransferRequest.objects.filter(
                company=company,
                status=UserBranchTransferRequest.STATUS_PENDING_APPROVAL
            ).select_related(
                'user',
                'from_branch',
                'to_branch',
                'initiated_by'
            )
        
        return JsonResponse({
            'success': True,
            'data': {
                'pending_selection': [
                    serialize_transfer_request(tr) for tr in pending_selection
                ],
                'pending_approval': [
                    serialize_transfer_request(tr) for tr in pending_approval
                ],
            }
        })
    
    except Exception as e:
        logger.error(f'Get pending transfers error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to retrieve pending transfers',
            'details': str(e)
        }, status=500)


# ============================================================================
# USER SELF-SERVICE: INITIATION & MANAGER APPROVAL
# ============================================================================

@csrf_protect
@login_required
@require_http_methods(['POST'])
def user_initiate_transfer(request):
    """
    User initiates their own branch transfer request.
    
    POST /users/api/transfer/user-initiate/
    {
        "to_branch_id": 5,
        "reason": "Relocating to London office for new role",
        "effective_date": "2025-01-15",  // optional
        "metadata": {}  // optional
    }
    
    Returns:
        201: Transfer request created successfully
        400: Validation error
        403: Permission denied
        500: Server error
    """
    
    try:
        # Parse request data
        data = json.loads(request.body)
        to_branch_id = data.get('to_branch_id')
        reason = data.get('reason', '').strip()
        effective_date = data.get('effective_date')
        metadata = data.get('metadata', {})
        
        # Validation
        if not to_branch_id:
            return JsonResponse({
                'success': False,
                'error': 'Destination branch is required'
            }, status=400)
        
        if not reason:
            return JsonResponse({
                'success': False,
                'error': 'Reason is required'
            }, status=400)
        
        if len(reason) < 10:
            return JsonResponse({
                'success': False,
                'error': 'Reason must be at least 10 characters'
            }, status=400)
        
        # Get branch
        try:
            to_branch = Branch.objects.get(
                id=to_branch_id,
                company=request.user.company,
                is_active=True
            )
        except Branch.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid destination branch'
            }, status=400)
        
        # Check user not already in that branch
        if request.user.primary_branch == to_branch:
            return JsonResponse({
                'success': False,
                'error': 'You are already in this branch'
            }, status=400)
        
        # Create transfer request via service
        result = UserBranchTransferService.user_initiate_transfer(
            user=request.user,
            to_branch=to_branch,
            reason=reason,
            effective_date=effective_date,
            metadata=metadata
        )
        
        if not result.success:
            return JsonResponse({
                'success': False,
                'error': result.message
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': result.message,
            'data': result.data
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f'User initiate transfer error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your request',
            'details': str(e)
        }, status=500)


@csrf_protect
@login_required
@require_http_methods(['POST'])
def manager_approve_transfer(request, transfer_id):
    """
    Manager approves user-initiated transfer request.
    
    POST /users/api/transfer/<id>/manager-approve/
    {
        "approval_reason": "Approved for department reorganization"  // optional
    }
    
    Returns:
        200: Transfer approved successfully
        400: Validation error
        403: Permission denied
        404: Transfer not found
        500: Server error
    """
    
    try:
        # Get transfer request
        try:
            transfer_request = UserBranchTransferRequest.objects.select_related(
                'user', 'from_branch', 'to_branch', 'initiated_by'
            ).get(
                id=transfer_id,
                company=request.user.company
            )
        except UserBranchTransferRequest.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Transfer request not found'
            }, status=404)
        
        # Parse request data
        data = json.loads(request.body) if request.body else {}
        approval_reason = data.get('approval_reason', '').strip()
        
        # Approve via service
        result = UserBranchTransferService.manager_approve_transfer(
            transfer_request=transfer_request,
            manager=request.user,
            approval_reason=approval_reason
        )
        
        if not result.success:
            return JsonResponse({
                'success': False,
                'error': result.message
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': result.message,
            'data': result.data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f'Manager approve transfer error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your request',
            'details': str(e)
        }, status=500)


@csrf_protect
@login_required
@require_http_methods(['POST'])
def manager_reject_transfer(request, transfer_id):
    """
    Manager rejects user-initiated transfer request.
    
    POST /users/api/transfer/<id>/manager-reject/
    {
        "rejection_reason": "Cannot approve at this time due to staffing needs"
    }
    
    Returns:
        200: Transfer rejected successfully
        400: Validation error
        403: Permission denied
        404: Transfer not found
        500: Server error
    """
    
    try:
        # Get transfer request
        try:
            transfer_request = UserBranchTransferRequest.objects.select_related(
                'user', 'from_branch', 'to_branch', 'initiated_by'
            ).get(
                id=transfer_id,
                company=request.user.company
            )
        except UserBranchTransferRequest.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Transfer request not found'
            }, status=404)
        
        # Parse request data
        data = json.loads(request.body)
        rejection_reason = data.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            return JsonResponse({
                'success': False,
                'error': 'Rejection reason is required'
            }, status=400)
        
        # Reject via service
        result = UserBranchTransferService.manager_reject_transfer(
            transfer_request=transfer_request,
            manager=request.user,
            rejection_reason=rejection_reason
        )
        
        if not result.success:
            return JsonResponse({
                'success': False,
                'error': result.message
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': result.message,
            'data': result.data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f'Manager reject transfer error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your request',
            'details': str(e)
        }, status=500)


@csrf_protect
@login_required
@require_http_methods(['GET'])
def my_transfer_requests(request):
    """
    Get current user's transfer requests.
    
    GET /users/api/transfer/my-requests/
    
    Returns list of user's own transfer requests with full details.
    """
    
    try:
        # Get user's transfer requests
        requests = UserBranchTransferRequest.objects.filter(
            user=request.user,
            company=request.user.company
        ).select_related(
            'from_branch',
            'to_branch',
            'initiated_by',
            'approved_by',
            'manager_approved_by'
        ).prefetch_related(
            Prefetch(
                'asset_selections',
                queryset=AssetTransferSelection.objects.select_related('asset', 'asset__category')
            )
        ).order_by('-initiated_at')[:20]  # Limit to 20 most recent
        
        # Serialize requests
        serialized_requests = []
        for transfer_request in requests:
            data = serialize_transfer_request(transfer_request)
            
            # Add manager approval info for user-initiated transfers
            if transfer_request.initiation_type == UserBranchTransferRequest.INITIATION_TYPE_USER:
                data['initiation_type'] = 'user_initiated'
                data['manager_approved_by'] = {
                    'id': transfer_request.manager_approved_by.id,
                    'username': transfer_request.manager_approved_by.username,
                    'full_name': transfer_request.manager_approved_by.get_full_name() or transfer_request.manager_approved_by.username,
                } if transfer_request.manager_approved_by else None
                data['manager_approval_reason'] = transfer_request.manager_approval_reason
                data['timestamps']['manager_approval_at'] = transfer_request.manager_approval_at.isoformat() if transfer_request.manager_approval_at else None
            else:
                data['initiation_type'] = 'admin_initiated'
            
            serialized_requests.append(data)
        
        return JsonResponse({
            'success': True,
            'data': {
                'requests': serialized_requests,
                'count': len(serialized_requests)
            }
        })
        
    except Exception as e:
        logger.error(f'Get my transfer requests error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to retrieve your transfer requests',
            'details': str(e)
        }, status=500)
