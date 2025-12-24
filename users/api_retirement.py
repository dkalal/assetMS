"""
WORLD-CLASS: Self-Service Retirement API Endpoints

This module contains all API endpoints for the self-service retirement workflow.

Endpoints:
- User self-service: Submit, view, cancel requests
- Manager/Admin approval: List pending, approve, reject
- Admin processing: Start processing, asset handover, complete
- Dashboard & reporting: Stats, timeline, history

Security:
- Multi-tenancy enforcement
- Role-based access control
- CSRF protection
- Complete audit logging

Author: AI Software Engineer
Date: January 2025
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q, Count
from django.utils import timezone

from users.models import User, UserRetirement
from users.services.retirement import UserRetirementService
from assets.models import Asset
from users.decorators import api_admin_required, api_manager_or_admin_required
from tenancy.policy_service import PolicyService

logger = logging.getLogger(__name__)


# ============================================================================
# USER SELF-SERVICE ENDPOINTS
# ============================================================================

@login_required
@require_http_methods(["POST"])
@csrf_protect
def api_retirement_submit_request(request):
    """
    POST /api/retirement/request/
    
    User submits their own retirement request
    
    Body:
    {
        "effective_date": "2025-02-28",
        "reason_category": "resignation",
        "reason": "Accepting new position at another company",
        "notes": "Optional additional notes"
    }
    
    Returns:
    {
        "success": true,
        "retirement_id": "uuid",
        "status": "requested",
        "effective_date": "2025-02-28",
        "days_until_effective": 45,
        "asset_count": 5,
        "assets": [...],
        "message": "Retirement request submitted successfully"
    }
    """
    try:
        data = json.loads(request.body)
        
        # Parse and validate input
        effective_date_str = data.get('effective_date')
        reason_category = data.get('reason_category')
        reason = data.get('reason', '').strip()
        notes = data.get('notes', '').strip()
        
        # Validate required fields
        if not effective_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Effective date is required'
            }, status=400)
        
        if not reason_category:
            return JsonResponse({
                'success': False,
                'error': 'Reason category is required'
            }, status=400)
        
        if not reason:
            return JsonResponse({
                'success': False,
                'error': 'Reason is required'
            }, status=400)
        
        # Parse date
        try:
            effective_date = datetime.strptime(effective_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }, status=400)
        
        # Call service method
        result = UserRetirementService.submit_retirement_request(
            user=request.user,
            effective_date=effective_date,
            reason_category=reason_category,
            reason=reason,
            notes=notes
        )
        
        return JsonResponse(result)
        
    except ValidationError as e:
        logger.warning(f"Validation error in retirement request: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except PermissionDenied as e:
        logger.warning(f"Permission denied in retirement request: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=403)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error submitting retirement request: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_retirement_my_request(request):
    """
    GET /api/retirement/my-request/
    
    User views their own retirement request status
    
    Returns:
    {
        "success": true,
        "has_request": true,
        "retirement": {...}
    }
    """
    try:
        # Get user's active retirement request
        retirement = UserRetirement.objects.filter(
            user=request.user,
            company=request.user.company,
            status__in=[
                UserRetirement.STATUS_REQUESTED,
                UserRetirement.STATUS_PENDING_APPROVAL,
                UserRetirement.STATUS_APPROVED,
                UserRetirement.STATUS_IN_PROGRESS,
                UserRetirement.STATUS_ASSET_HANDOVER,
                UserRetirement.STATUS_FINAL_REVIEW
            ]
        ).select_related('reviewed_by', 'processed_by').first()
        
        if not retirement:
            return JsonResponse({
                'success': True,
                'has_request': False,
                'message': 'No active retirement request found'
            })
        
        # Get timeline events
        timeline = retirement.get_timeline_events()
        
        # Get asset info
        assets = Asset.objects.filter(
            assigned_to=request.user,
            company=request.user.company,
            status__in=[Asset.STATUS_ACTIVE, Asset.STATUS_IN_MAINTENANCE]
        ).select_related('category', 'branch')[:50]
        
        assets_list = []
        for asset in assets:
            asset_name = asset.category.name
            if asset.dynamic_data and isinstance(asset.dynamic_data, dict):
                asset_name = asset.dynamic_data.get('name', asset.category.name)
            
            assets_list.append({
                'id': asset.id,
                'name': asset_name,
                'category': asset.category.name,
                'branch': asset.branch.name if asset.branch else 'Unassigned',
                'status': asset.status
            })
        
        return JsonResponse({
            'success': True,
            'has_request': True,
            'retirement': {
                'id': str(retirement.id),
                'status': retirement.status,
                'status_display': retirement.get_status_display(),
                'status_color': retirement.get_approval_status_color(),
                'effective_date': retirement.effective_date.isoformat(),
                'days_until_effective': retirement.days_until_effective,
                'reason_category': retirement.reason_category,
                'reason': retirement.reason,
                'notes': retirement.notes,
                'asset_count': retirement.asset_count,
                'assets_returned': retirement.assets_returned,
                'assets_pending': retirement.assets_pending,
                'request_date': retirement.request_date.isoformat(),
                'reviewed_by': retirement.reviewed_by.get_full_name() if retirement.reviewed_by else None,
                'reviewed_at': retirement.reviewed_at.isoformat() if retirement.reviewed_at else None,
                'approval_notes': retirement.approval_notes,
                'rejection_reason': retirement.rejection_reason,
                'can_cancel': retirement.can_be_cancelled,
                'timeline': timeline,
                'assets': assets_list
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting user retirement request: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def api_retirement_cancel_my_request(request):
    """
    POST /api/retirement/my-request/cancel/
    
    User cancels their own retirement request
    
    Body:
    {
        "retirement_id": "uuid",
        "reason": "Changed my mind / Found another solution"
    }
    """
    try:
        data = json.loads(request.body)
        
        retirement_id = data.get('retirement_id')
        reason = data.get('reason', '').strip()
        
        if not retirement_id:
            return JsonResponse({
                'success': False,
                'error': 'Retirement ID is required'
            }, status=400)
        
        if not reason:
            return JsonResponse({
                'success': False,
                'error': 'Cancellation reason is required'
            }, status=400)
        
        # Call service method
        result = UserRetirementService.cancel_retirement_request_by_user(
            retirement_id=retirement_id,
            user=request.user,
            reason=reason
        )
        
        return JsonResponse(result)
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except PermissionDenied as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=403)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error cancelling retirement request: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


# ============================================================================
# MANAGER/ADMIN APPROVAL ENDPOINTS
# ============================================================================

@api_manager_or_admin_required
@require_http_methods(["GET"])
def api_retirement_pending_approvals(request):
    """
    GET /api/retirement/pending-approvals/
    
    List all pending retirement approvals for manager/admin
    
    Returns:
    {
        "success": true,
        "count": 5,
        "requests": [...]
    }
    """
    try:
        company = request.user.company
        
        # Base queryset: pending retirement requests for this company
        pending_qs = UserRetirement.objects.filter(
            company=company,
            status__in=[UserRetirement.STATUS_REQUESTED, UserRetirement.STATUS_PENDING_APPROVAL]
        ).select_related('user', 'requested_by')

        # Optional branch-level scoping for managers when enabled in policy
        if PolicyService.should_enforce_branch_scoping(request.user, company):
            accessible_branch_ids = list(PolicyService.get_accessible_branches(request.user, company))
            if accessible_branch_ids:
                pending_qs = pending_qs.filter(user__primary_branch_id__in=accessible_branch_ids)
            else:
                pending_qs = pending_qs.none()

        pending = pending_qs.order_by('request_date')
        
        requests_list = []
        for retirement in pending:
            requests_list.append({
                'id': str(retirement.id),
                'user': {
                    'id': retirement.user.id,
                    'name': retirement.user.get_full_name(),
                    'email': retirement.user.email,
                    'role': retirement.user.get_role_display(),
                    'branch': retirement.user.primary_branch.name if retirement.user.primary_branch else 'Unassigned'
                },
                'request_date': retirement.request_date.isoformat(),
                'effective_date': retirement.effective_date.isoformat(),
                'days_until_effective': retirement.days_until_effective,
                'reason_category': retirement.reason_category,
                'reason_category_display': retirement.get_reason_category_display(),
                'reason': retirement.reason[:200],  # First 200 chars for list view
                'asset_count': retirement.asset_count,
                'status': retirement.status,
                'status_display': retirement.get_status_display()
            })
        
        return JsonResponse({
            'success': True,
            'count': len(requests_list),
            'requests': requests_list
        })
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@api_manager_or_admin_required
@require_http_methods(["POST"])
@csrf_protect
def api_retirement_approve(request, retirement_id):
    """
    POST /api/retirement/<uuid>/approve/
    
    Approve a retirement request
    
    Body:
    {
        "comments": "Approved. Best wishes for your future endeavors."
    }
    """
    try:
        data = json.loads(request.body)
        comments = data.get('comments', '').strip()
        
        # Call service method
        result = UserRetirementService.approve_retirement_request(
            retirement_id=str(retirement_id),
            approver=request.user,
            comments=comments
        )
        
        return JsonResponse(result)
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except PermissionDenied as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=403)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error approving retirement: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@api_manager_or_admin_required
@require_http_methods(["POST"])
@csrf_protect
def api_retirement_reject(request, retirement_id):
    """
    POST /api/retirement/<uuid>/reject/
    
    Reject a retirement request
    
    Body:
    {
        "rejection_reason": "Need more information about transition plan"
    }
    """
    try:
        data = json.loads(request.body)
        rejection_reason = data.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            return JsonResponse({
                'success': False,
                'error': 'Rejection reason is required'
            }, status=400)
        
        # Call service method
        result = UserRetirementService.reject_retirement_request(
            retirement_id=str(retirement_id),
            reviewer=request.user,
            rejection_reason=rejection_reason
        )
        
        return JsonResponse(result)
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except PermissionDenied as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=403)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error rejecting retirement: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


# ============================================================================
# ADMIN PROCESSING ENDPOINTS
# ============================================================================

@api_admin_required
@require_http_methods(["GET"])
def api_retirement_approved_list(request):
    """
    GET /api/retirement/approved-requests/
    
    List all approved retirement requests ready for processing
    """
    try:
        company = request.user.company

        # Get approved and in-progress retirement requests for this company
        approved = UserRetirement.objects.filter(
            company=company,
            status__in=[
                UserRetirement.STATUS_APPROVED,
                UserRetirement.STATUS_IN_PROGRESS,
            ]
        ).select_related('user', 'reviewed_by').order_by('effective_date')

        requests_list = []
        for retirement in approved:
            requests_list.append({
                'id': str(retirement.id),
                'user': {
                    'id': retirement.user.id,
                    'name': retirement.user.get_full_name(),
                    'email': retirement.user.email,
                    'role': retirement.user.get_role_display(),
                },
                'request_date': retirement.request_date.isoformat() if retirement.request_date else None,
                'effective_date': retirement.effective_date.isoformat(),
                'days_until_effective': retirement.days_until_effective,
                'is_effective_date_reached': retirement.is_effective_date_reached,
                'asset_count': retirement.asset_count,
                'status': retirement.status,
                'status_display': retirement.get_status_display(),
                'reason': retirement.reason[:200] if retirement.reason else '',
                'reason_category': retirement.reason_category,
                'reason_category_display': retirement.get_reason_category_display(),
                'approved_by': retirement.reviewed_by.get_full_name() if retirement.reviewed_by else None,
                'approved_at': retirement.reviewed_at.isoformat() if retirement.reviewed_at else None,
            })

        return JsonResponse({
            'success': True,
            'count': len(requests_list),
            'requests': requests_list,
        })

    except Exception as e:
        logger.error(f"Error getting approved requests: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@api_admin_required
@require_http_methods(["POST"])
@csrf_protect
def api_retirement_start_processing(request, retirement_id):
    """
    POST /api/retirement/<uuid>/start/
    
    Start processing an approved retirement
    """
    try:
        # Call service method
        result = UserRetirementService.start_retirement_processing(
            retirement_id=str(retirement_id),
            admin=request.user
        )
        
        return JsonResponse(result)
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except PermissionDenied as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=403)
    except Exception as e:
        logger.error(f"Error starting retirement processing: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


# ============================================================================
# DASHBOARD & REPORTING ENDPOINTS
# ============================================================================

@api_manager_or_admin_required
@require_http_methods(["GET"])
def api_retirement_dashboard_stats(request):
    """
    GET /api/retirement/dashboard/
    
    Get retirement statistics for dashboard
    """
    try:
        company = request.user.company
        
        # Base queryset: all retirements for this company
        base_qs = UserRetirement.objects.filter(company=company)

        # Optional branch-level scoping for managers when enabled in policy
        if PolicyService.should_enforce_branch_scoping(request.user, company):
            accessible_branch_ids = list(PolicyService.get_accessible_branches(request.user, company))
            if accessible_branch_ids:
                base_qs = base_qs.filter(user__primary_branch_id__in=accessible_branch_ids)
            else:
                base_qs = base_qs.none()
        
        # Get counts by status from scoped queryset
        stats = base_qs.values('status').annotate(count=Count('id'))
        
        status_counts = {item['status']: item['count'] for item in stats}
        
        # Get recent requests (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_count = base_qs.filter(
            request_date__gte=thirty_days_ago
        ).count()
        
        # Get upcoming effective dates (next 30 days)
        today = date.today()
        thirty_days_later = today + timedelta(days=30)
        upcoming = base_qs.filter(
            effective_date__gte=today,
            effective_date__lte=thirty_days_later,
            status__in=[
                UserRetirement.STATUS_APPROVED,
                UserRetirement.STATUS_IN_PROGRESS,
                UserRetirement.STATUS_ASSET_HANDOVER
            ]
        ).count()
        
        return JsonResponse({
            'success': True,
            'pending_approvals': status_counts.get(UserRetirement.STATUS_REQUESTED, 0) + 
                               status_counts.get(UserRetirement.STATUS_PENDING_APPROVAL, 0),
            'approved_requests': status_counts.get(UserRetirement.STATUS_APPROVED, 0),
            'in_progress': status_counts.get(UserRetirement.STATUS_IN_PROGRESS, 0) +
                          status_counts.get(UserRetirement.STATUS_ASSET_HANDOVER, 0),
            'completed_this_month': status_counts.get(UserRetirement.STATUS_COMPLETED, 0),
            'rejected': status_counts.get(UserRetirement.STATUS_REJECTED, 0),
            'total_active': status_counts.get(UserRetirement.STATUS_REQUESTED, 0) + 
                          status_counts.get(UserRetirement.STATUS_PENDING_APPROVAL, 0) +
                          status_counts.get(UserRetirement.STATUS_APPROVED, 0) +
                          status_counts.get(UserRetirement.STATUS_IN_PROGRESS, 0),
            'recent_requests_30d': recent_count,
            'upcoming_effective_dates_30d': upcoming
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@api_manager_or_admin_required
@require_http_methods(["GET"])
def api_retirement_timeline(request, retirement_id):
    """
    GET /api/retirement/<uuid>/timeline/
    
    Get detailed timeline for a retirement request
    """
    try:
        company = request.user.company
        
        # Get retirement with all related info
        retirement = UserRetirement.objects.select_related(
            'user', 'requested_by', 'reviewed_by', 'processed_by', 'completed_by'
        ).get(id=retirement_id, company=company)

        # Optional branch-level permission check for managers
        if PolicyService.should_enforce_branch_scoping(request.user, company):
            accessible_branch_ids = list(PolicyService.get_accessible_branches(request.user, company))
            user_branch_id = getattr(retirement.user, 'primary_branch_id', None)
            if not accessible_branch_ids or user_branch_id not in accessible_branch_ids:
                return JsonResponse({
                    'success': False,
                    'error': 'Insufficient permissions for this retirement request'
                }, status=403)
        
        # Get timeline events
        timeline = retirement.get_timeline_events()
        
        return JsonResponse({
            'success': True,
            'retirement_id': str(retirement.id),
            'timeline': timeline
        })
        
    except UserRetirement.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Retirement request not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting retirement timeline: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)
