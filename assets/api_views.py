from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from tenancy.models import Alert
from users.decorators import api_login_required
from users.utils import can

from assets.serializers import (
    AdminReviewForm,
    InitiateTransferForm,
    ReceiverDecisionForm,
)
from assets.services.transfers import (
    admin_review,
    initiate_transfer,
    receiver_review,
)


def _json_error(message: str, *, status: int = 400, code: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> JsonResponse:
    payload: Dict[str, Any] = {
        "success": False,
        "error": message,
    }
    if code:
        payload["code"] = code
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


def _company_from_request(request) -> Optional[Any]:  # pragma: no cover - thin helper
    return getattr(request, "company", None) or getattr(request.user, "company", None)


def _parse_body(request) -> Dict[str, Any]:
    if request.content_type in {"application/json", "application/json; charset=utf-8"}:
        try:
            return json.loads(request.body or "{}")
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON payload.")
    return request.POST.dict()


@api_login_required
@require_http_methods(["POST"])
def api_transfer_initiate(request):
    """
    WORLD-CLASS: Initiate asset transfer
    
    Permission Logic (following ServiceNow ITAM, IBM Maximo, SAP EAM):
    - Admins: Can transfer any asset in their company
    - Managers: Can transfer any asset (have edit_assets permission)
    - Users: Can transfer assets assigned to them OR unassigned assets in their branches
    
    CSRF Protection: Provided by CsrfViewMiddleware (global)
    """
    try:
        payload = _parse_body(request)
    except ValidationError as exc:
        return _json_error(str(exc), status=400)

    form = InitiateTransferForm(user=request.user, company=_company_from_request(request), data=payload)
    if not form.is_valid():
        return JsonResponse({"success": False, "errors": form.errors}, status=400)
    
    # WORLD-CLASS: Permission check based on role and ownership
    # Get the asset from the form's cleaned data
    asset = form.cleaned_data.get("asset")
    user = request.user
    
    # Check if user has permission to transfer this specific asset
    has_permission = False
    
    if can(user, "edit_assets"):
        # Admins and Managers can transfer any asset
        has_permission = True
    else:
        # Regular users can transfer:
        # 1. Assets assigned to them (ownership-based)
        # 2. Unassigned assets in their accessible branches
        if asset.assigned_to_id == user.pk:
            has_permission = True
        elif not asset.assigned_to_id:
            # Check if asset is in user's accessible branches
            try:
                from tenancy.policy_service import PolicyService
                accessible_branch_ids = PolicyService.get_accessible_branches(user, asset.company)
                has_permission = asset.branch_id in accessible_branch_ids
            except Exception:
                # Fallback: check if asset is in user's primary branch
                has_permission = (
                    hasattr(user, 'primary_branch') and 
                    user.primary_branch and 
                    asset.branch_id == user.primary_branch.id
                )
    
    if not has_permission:
        return _json_error(
            "You do not have permission to transfer this asset. You can only transfer assets assigned to you or unassigned assets in your branches.",
            status=403,
            code="INSUFFICIENT_PERMISSIONS"
        )

    cleaned = form.cleaned_data
    try:
        transfer = initiate_transfer(
            initiator=request.user,
            asset=cleaned["asset"],
            to_user=cleaned["to_user"],
            to_branch=cleaned.get("to_branch"),
            initiator_comment=cleaned.get("initiator_comment", ""),
            context=cleaned.get("context", {}),
        )
    except ValidationError as exc:
        return _json_error(str(exc), status=400)
    except PermissionDenied as exc:
        return _json_error(str(exc), status=403)

    response = {
        "success": True,
        "transfer": {
            "id": transfer.pk,
            "asset_id": transfer.asset_id,
            "asset_uuid": str(transfer.asset.uuid),
            "state": transfer.state,
            "receiver_id": transfer.to_user_id,
            "created_at": transfer.created_at.isoformat(),
        },
    }
    return JsonResponse(response, status=201)


@api_login_required
@require_http_methods(["POST"])
def api_transfer_receiver_decision(request):
    """
    WORLD-CLASS: Receiver decision on asset transfer
    
    CSRF Protection: Provided by CsrfViewMiddleware (global)
    """
    try:
        payload = _parse_body(request)
    except ValidationError as exc:
        return _json_error(str(exc), status=400)

    form = ReceiverDecisionForm(user=request.user, data=payload)
    if not form.is_valid():
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    cleaned = form.cleaned_data
    try:
        transfer = receiver_review(
            transfer=cleaned["transfer"],
            receiver=request.user,
            decision=cleaned["decision"],
            comment=cleaned.get("comment", ""),
        )
    except ValidationError as exc:
        return _json_error(str(exc), status=400)
    except PermissionDenied as exc:
        return _json_error(str(exc), status=403)

    return JsonResponse(
        {
            "success": True,
            "transfer": {
                "id": transfer.pk,
                "state": transfer.state,
                "receiver_decision": transfer.receiver_decision,
                "receiver_comment": transfer.receiver_comment,
                "receiver_decided_at": transfer.receiver_decided_at.isoformat() if transfer.receiver_decided_at else None,
            },
        }
    )


@api_login_required
@require_http_methods(["POST"])
def api_transfer_admin_review(request):
    """
    WORLD-CLASS: Admin/Manager review of asset transfer
    
    CSRF Protection: Provided by CsrfViewMiddleware (global)
    """
    if getattr(request.user, "role", "user") not in {"admin", "manager"} and not can(request.user, "edit_assets"):
        return _json_error("Administrative privileges required.", status=403, code="INSUFFICIENT_PERMISSIONS")

    try:
        payload = _parse_body(request)
    except ValidationError as exc:
        return _json_error(str(exc), status=400)

    form = AdminReviewForm(user=request.user, company=_company_from_request(request), data=payload)
    if not form.is_valid():
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    cleaned = form.cleaned_data
    try:
        transfer = admin_review(
            transfer=cleaned["transfer"],
            reviewer=request.user,
            decision=cleaned["decision"],
            comment=cleaned.get("comment", ""),
        )
    except ValidationError as exc:
        return _json_error(str(exc), status=400)
    except PermissionDenied as exc:
        return _json_error(str(exc), status=403)

    return JsonResponse(
        {
            "success": True,
            "transfer": {
                "id": transfer.pk,
                "state": transfer.state,
                "admin_decision": transfer.admin_decision,
                "admin_comment": transfer.admin_comment,
                "admin_decided_at": transfer.admin_decided_at.isoformat() if transfer.admin_decided_at else None,
            },
        }
    )


@api_login_required
@require_http_methods(["POST"])
def api_transfer_cancel(request):
    """
    WORLD-CLASS: Cancel a pending transfer (initiator or admin only)
    
    CSRF Protection: Provided by CsrfViewMiddleware (global)
    """
    try:
        payload = _parse_body(request)
    except ValidationError as exc:
        return _json_error(str(exc), status=400)
    
    transfer_id = payload.get("transfer_id")
    if not transfer_id:
        return _json_error("Transfer ID is required.", status=400)
    
    try:
        from assets.models import AssetTransfer
        transfer = AssetTransfer.objects.select_related("asset", "initiator", "to_user").get(pk=transfer_id)
    except AssetTransfer.DoesNotExist:
        return _json_error("Transfer not found.", status=404)
    
    # Permission check: Only initiator or admin/manager can cancel
    user = request.user
    is_initiator = transfer.initiator_id == user.id
    is_admin_or_manager = getattr(user, "role", "user") in {"admin", "manager"}
    
    if not (is_initiator or is_admin_or_manager):
        return _json_error("You do not have permission to cancel this transfer.", status=403)
    
    # Multi-tenancy check
    if hasattr(user, "company_id") and transfer.company_id != user.company_id:
        return _json_error("Transfer does not belong to your company.", status=403)
    
    # State check: Can only cancel active transfers
    if transfer.state not in AssetTransfer.ACTIVE_STATES:
        return _json_error(f"Cannot cancel transfer in '{transfer.get_state_display()}' state.", status=400)
    
    # Cancel the transfer
    from django.db import transaction
    from django.utils import timezone
    from audit.utils import log_audit
    
    with transaction.atomic():
        transfer.state = AssetTransfer.TransferState.CANCELLED
        transfer.admin_decision = AssetTransfer.Decision.REJECTED
        transfer.admin_comment = f"Cancelled by {user.get_full_name() or user.username}"
        transfer.admin_decided_at = timezone.now()
        transfer.save(update_fields=["state", "admin_decision", "admin_comment", "admin_decided_at", "updated_at"])
        
        # Log audit event
        log_audit(
            user,
            "transfer_cancelled",
            transfer.asset,
            f"Transfer cancelled by {user.get_full_name() or user.username}",
            company=transfer.company,
            branch=transfer.from_branch or transfer.asset.branch,
            related_user=transfer.to_user,
        )
        
        # Create alert for recipient if different from canceller
        if transfer.to_user_id and transfer.to_user_id != user.id:
            from tenancy.models import Alert
            Alert.objects.create(
                company_id=transfer.company_id,
                branch_id=transfer.to_branch_id,
                recipient_id=transfer.to_user_id,
                level=Alert.LEVEL_INFO,
                message=f"Transfer for {transfer.asset} has been cancelled.",
                context={
                    "transfer_id": transfer.pk,
                    "asset_id": transfer.asset_id,
                    "cancelled_by": user.id,
                },
            )
    
    return JsonResponse(
        {
            "success": True,
            "message": "Transfer cancelled successfully.",
            "transfer": {
                "id": transfer.pk,
                "state": transfer.state,
            },
        }
    )


def _serialize_alert(alert: Alert) -> Dict[str, Any]:
    return {
        "id": alert.pk,
        "level": alert.level,
        "message": alert.message,
        "context": alert.context,
        "is_read": alert.is_read,
        "created_at": alert.created_at.isoformat(),
        "read_at": alert.read_at.isoformat() if alert.read_at else None,
        "branch_id": alert.branch_id,
    }


def _filter_alerts_for_request(request) -> Iterable[Alert]:
    company = _company_from_request(request)
    qs = Alert.objects.filter(recipient=request.user).order_by("-created_at")
    if company:
        qs = qs.filter(company=company)
    return qs


@api_login_required
@require_http_methods(["GET", "POST"])
def api_transfer_alerts(request):
    """
    WORLD-CLASS: Transfer alerts management
    
    CSRF Protection: Provided by CsrfViewMiddleware (global)
    """
    if request.method == "GET":
        limit_raw = request.GET.get("limit", 20)
        try:
            limit = max(1, min(int(limit_raw), 50))
        except (TypeError, ValueError):
            limit = 20

        include_read = request.GET.get("include_read") == "1"
        alerts_qs = _filter_alerts_for_request(request)
        if not include_read:
            alerts_qs = alerts_qs.filter(is_read=False)

        items = [_serialize_alert(alert) for alert in alerts_qs[:limit]]
        return JsonResponse({
            "success": True,
            "alerts": items,
            "count": len(items),
        })

    # POST: mark alerts read/unread
    try:
        payload = _parse_body(request)
    except ValidationError as exc:
        return _json_error(str(exc), status=400)

    action = payload.get("action", "mark_read")
    alert_ids = payload.get("alert_ids") or payload.get("ids")
    if isinstance(alert_ids, (str, int)):
        alert_ids = [alert_ids]

    if not isinstance(alert_ids, (list, tuple)) or not alert_ids:
        return _json_error("alert_ids must be a non-empty list.", status=400)

    try:
        normalized_ids = [int(alert_id) for alert_id in alert_ids]
    except (TypeError, ValueError):
        return _json_error("alert_ids must contain integers.", status=400)

    alerts = _filter_alerts_for_request(request).filter(pk__in=normalized_ids)
    if not alerts.exists():
        return _json_error("No matching alerts found for this user.", status=404)

    now = timezone.now()
    update_kwargs = {}
    if action == "mark_unread":
        update_kwargs.update({"is_read": False, "read_at": None})
    else:
        update_kwargs.update({"is_read": True, "read_at": now})
    if hasattr(Alert, "updated_at"):
        update_kwargs["updated_at"] = now
    alerts.update(**update_kwargs)

    refreshed = [_serialize_alert(alert) for alert in alerts]
    return JsonResponse({
        "success": True,
        "alerts": refreshed,
        "action": action,
    })


@api_login_required
@require_http_methods(["GET"])
def api_category_fields_enhanced(request):
    """
    Enhanced API supporting all wizard field types (text, number, date, select, textarea, file)
    Returns comprehensive field metadata for dynamic rendering in asset registration
    
    NOTE: Current model only has: key, label, type, required
    Future fields (options, min_value, etc.) will be added via migrations
    """
    category_id = request.GET.get('category_id')
    company = _company_from_request(request)
    
    if not category_id:
        return _json_error('Category ID required', status=400, code='MISSING_CATEGORY_ID')
    
    if not company:
        return _json_error('Company context required', status=403, code='MISSING_COMPANY_CONTEXT')
    
    try:
        from .models import AssetCategory, AssetCategoryField
        
        category = AssetCategory.objects.for_company(company).get(pk=category_id)
        fields_qs = AssetCategoryField.objects.for_company(company).filter(
            category=category
        ).order_by('id')
        
        fields_data = {}
        for field in fields_qs:
            # Core fields that exist in current model
            field_info = {
                'key': field.key,
                'label': field.label,
                'type': field.type,
                'required': field.required,
            }
            
            # Optional fields with safe defaults (defensive programming)
            field_info['help_text'] = getattr(field, 'help_text', '')
            field_info['placeholder'] = getattr(field, 'placeholder', '')
            
            # Type-specific metadata (safely check if attributes exist)
            if field.type == 'select':
                field_info['options'] = getattr(field, 'options', [])
            
            if field.type == 'number':
                field_info['min_value'] = getattr(field, 'min_value', None)
                field_info['max_value'] = getattr(field, 'max_value', None)
            
            if field.type in ['text', 'textarea']:
                # Default max_length based on type
                default_max = 255 if field.type == 'text' else 1000
                field_info['max_length'] = getattr(field, 'max_length', default_max)
            
            fields_data[field.key] = field_info
        
        # Category info (safely handle missing attributes)
        category_info = {
            'id': category.id,
            'name': category.name,
            'description': getattr(category, 'description', ''),
            'template_name': getattr(category, 'template_name', None),
        }
        
        return JsonResponse({
            'success': True,
            'fields': fields_data,
            'category': category_info,
        })
        
    except AssetCategory.DoesNotExist:
        return _json_error('Category not found', status=404, code='CATEGORY_NOT_FOUND')
    except Exception as e:
        # Log the error for debugging
        import traceback
        traceback.print_exc()
        return _json_error(f'Server error: {str(e)}', status=500, code='SERVER_ERROR')


@api_login_required
@require_http_methods(["GET"])
def api_check_duplicate_assets(request):
    """
    Phase 1: Duplicate Detection API
    Check for potential duplicate assets based on category and dynamic field values.
    Returns list of similar assets with similarity score.
    
    Query params:
    - category_id: Required
    - dynamic_data: JSON string of field values
    - exclude_uuid: Optional UUID to exclude (for edit forms)
    """
    company = _company_from_request(request)
    if not company:
        return _json_error('Company context required', status=403, code='MISSING_COMPANY_CONTEXT')
    
    category_id = request.GET.get('category_id')
    if not category_id:
        return _json_error('Category ID required', status=400, code='MISSING_CATEGORY_ID')
    
    try:
        from .models import Asset, AssetCategory
        
        # Parse dynamic data
        dynamic_data_raw = request.GET.get('dynamic_data', '{}')
        try:
            dynamic_data = json.loads(dynamic_data_raw)
        except json.JSONDecodeError:
            return _json_error('Invalid dynamic_data JSON', status=400)
        
        # Get category
        try:
            category = AssetCategory.objects.for_company(company).get(pk=category_id)
        except AssetCategory.DoesNotExist:
            return _json_error('Category not found', status=404)
        
        # Find assets in same category
        assets_qs = Asset.objects.for_company(company).filter(
            category=category,
            status__in=['active', 'in_maintenance']  # Only check active assets
        ).select_related('category', 'assigned_to')
        
        # Exclude specific UUID if provided (for edit forms)
        exclude_uuid = request.GET.get('exclude_uuid')
        if exclude_uuid:
            assets_qs = assets_qs.exclude(uuid=exclude_uuid)
        
        # Calculate similarity scores
        duplicates = []
        for asset in assets_qs[:100]:  # Limit to 100 for performance
            similarity_score = _calculate_similarity(dynamic_data, asset.dynamic_data)
            
            # Only include if similarity > 60%
            if similarity_score >= 60:
                duplicates.append({
                    'id': asset.pk,
                    'uuid': str(asset.uuid),
                    'category': asset.category.name,
                    'status': asset.status,
                    'assigned_to': asset.assigned_to.username if asset.assigned_to else None,
                    'created_at': asset.created_at.isoformat(),
                    'similarity_score': similarity_score,
                    'matching_fields': _get_matching_fields(dynamic_data, asset.dynamic_data),
                })
        
        # Sort by similarity score (highest first)
        duplicates.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return JsonResponse({
            'success': True,
            'duplicates': duplicates[:10],  # Return top 10
            'count': len(duplicates),
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _json_error(f'Server error: {str(e)}', status=500)


@api_login_required
@require_http_methods(["GET"])
def api_smart_suggestions(request):
    """
    Phase 1: Smart Auto-Complete API
    Provide intelligent field value suggestions based on historical data.
    
    Query params:
    - category_id: Required
    - field_key: Required (e.g., 'serial_number', 'manufacturer')
    - query: Optional search term for filtering
    - limit: Optional (default 10, max 20)
    """
    company = _company_from_request(request)
    if not company:
        return _json_error('Company context required', status=403, code='MISSING_COMPANY_CONTEXT')
    
    category_id = request.GET.get('category_id')
    field_key = request.GET.get('field_key')
    
    if not category_id or not field_key:
        return _json_error('category_id and field_key required', status=400)
    
    try:
        from .models import Asset, AssetCategory
        from django.db.models import Count
        
        # Get category
        try:
            category = AssetCategory.objects.for_company(company).get(pk=category_id)
        except AssetCategory.DoesNotExist:
            return _json_error('Category not found', status=404)
        
        # Get limit
        try:
            limit = min(int(request.GET.get('limit', 10)), 20)
        except (TypeError, ValueError):
            limit = 10
        
        # Get query filter
        query_term = request.GET.get('query', '').strip().lower()
        
        # Get assets in same category
        assets = Asset.objects.for_company(company).filter(
            category=category,
            status__in=['active', 'in_maintenance', 'retired']
        ).values_list('dynamic_data', flat=True)
        
        # Extract unique values for the field
        value_counts = {}
        for data in assets:
            if isinstance(data, dict) and field_key in data:
                value = data[field_key]
                if value and isinstance(value, str):
                    value_lower = value.lower()
                    # Filter by query if provided
                    if not query_term or query_term in value_lower:
                        if value not in value_counts:
                            value_counts[value] = 0
                        value_counts[value] += 1
        
        # Sort by frequency (most common first)
        suggestions = [
            {'value': value, 'count': count}
            for value, count in sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
        ][:limit]
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions,
            'field_key': field_key,
            'category_id': int(category_id),
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _json_error(f'Server error: {str(e)}', status=500)


def _calculate_similarity(data1: Dict[str, Any], data2: Dict[str, Any]) -> int:
    """
    Calculate similarity score between two dynamic_data dictionaries.
    Returns percentage (0-100) based on matching field values.
    """
    if not data1 or not data2:
        return 0
    
    # Get all keys from both dicts
    all_keys = set(data1.keys()) | set(data2.keys())
    if not all_keys:
        return 0
    
    matching = 0
    for key in all_keys:
        val1 = data1.get(key)
        val2 = data2.get(key)
        
        # Skip empty values
        if not val1 or not val2:
            continue
        
        # Normalize and compare
        if isinstance(val1, str) and isinstance(val2, str):
            if val1.strip().lower() == val2.strip().lower():
                matching += 1
        elif val1 == val2:
            matching += 1
    
    # Calculate percentage
    return int((matching / len(all_keys)) * 100)


def _get_matching_fields(data1: Dict[str, Any], data2: Dict[str, Any]) -> list:
    """
    Get list of field keys that match between two dynamic_data dictionaries.
    """
    matching_fields = []
    all_keys = set(data1.keys()) & set(data2.keys())
    
    for key in all_keys:
        val1 = data1.get(key)
        val2 = data2.get(key)
        
        if val1 and val2:
            if isinstance(val1, str) and isinstance(val2, str):
                if val1.strip().lower() == val2.strip().lower():
                    matching_fields.append(key)
            elif val1 == val2:
                matching_fields.append(key)
    
    return matching_fields


@api_login_required
@require_http_methods(["GET"])
def api_transfer_list(request):
    """
    List asset transfers for the authenticated user's company.
    WORLD-CLASS MULTI-TENANCY: Automatic role-based filtering.
    - Users: See only transfers where they are initiator, sender, or receiver
    - Managers: See transfers in their accessible branches
    - Admins: See all company transfers
    """
    from assets.models import AssetTransfer
    from django.db.models import Q
    
    company = _company_from_request(request)
    if not company:
        return _json_error("Company context required", status=403, code="MISSING_COMPANY_CONTEXT")
    
    user = request.user
    role = getattr(user, 'role', 'user')
    
    # Base queryset with company scoping
    transfers = AssetTransfer.objects.filter(company=company).select_related(
        'asset', 'asset__category', 'initiator', 'from_user', 'to_user',
        'from_branch', 'to_branch', 'approved_by'
    ).order_by('-created_at')
    
    # WORLD-CLASS: Automatic role-based filtering (security at API level)
    if role == 'user':
        # Users see only transfers where they are involved
        transfers = transfers.filter(
            Q(initiator=user) | Q(to_user=user) | Q(from_user=user)
        )
    elif role == 'manager':
        # Managers see transfers in their accessible branches
        from tenancy.policy_service import PolicyService
        try:
            accessible_branch_ids = PolicyService.get_accessible_branches(user, company)
            transfers = transfers.filter(
                Q(from_branch_id__in=accessible_branch_ids) |
                Q(to_branch_id__in=accessible_branch_ids) |
                Q(asset__branch_id__in=accessible_branch_ids)
            )
        except Exception:
            # Fallback: show only transfers where manager is involved
            transfers = transfers.filter(
                Q(initiator=user) | Q(to_user=user) | Q(from_user=user)
            )
    # Admin sees all company transfers (no additional filter)
    
    # Optional status filter (for UX enhancement, not security)
    status = request.GET.get('status')
    if status:
        transfers = transfers.filter(state=status)
    
    # Optional role filter (for UX enhancement, further narrows results)
    role_filter = request.GET.get('role')
    if role_filter == 'receiver':
        transfers = transfers.filter(to_user=user)
    elif role_filter == 'initiator':
        transfers = transfers.filter(initiator=user)
    elif role_filter == 'admin' and role == 'admin':
        transfers = transfers.filter(state=AssetTransfer.TransferState.AWAITING_ADMIN)
    
    # Serialize transfers
    transfers_data = []
    for transfer in transfers[:100]:  # Limit to 100 for performance
        transfers_data.append({
            'id': transfer.pk,
            'asset_id': transfer.asset_id,
            'asset': {
                'id': transfer.asset.pk,
                'name': transfer.asset.dynamic_data.get('name', f'Asset #{transfer.asset.pk}'),
                'uuid': str(transfer.asset.uuid),
                'category': transfer.asset.category.name,
            } if transfer.asset else None,
            'state': transfer.state,
            'initiator_id': transfer.initiator_id,
            'initiator': {
                'id': transfer.initiator.pk,
                'name': transfer.initiator.get_full_name() or transfer.initiator.username,
            } if transfer.initiator else None,
            'from_user_id': transfer.from_user_id,
            'from_user': {
                'id': transfer.from_user.pk,
                'name': transfer.from_user.get_full_name() or transfer.from_user.username,
            } if transfer.from_user else None,
            'to_user_id': transfer.to_user_id,
            'to_user': {
                'id': transfer.to_user.pk,
                'name': transfer.to_user.get_full_name() or transfer.to_user.username,
            } if transfer.to_user else None,
            'from_branch_id': transfer.from_branch_id,
            'from_branch': {
                'id': transfer.from_branch.pk,
                'name': transfer.from_branch.name,
            } if transfer.from_branch else None,
            'to_branch_id': transfer.to_branch_id,
            'to_branch': {
                'id': transfer.to_branch.pk,
                'name': transfer.to_branch.name,
            } if transfer.to_branch else None,
            'reason': transfer.reason,
            'receiver_decision': transfer.receiver_decision,
            'receiver_comment': transfer.receiver_comment,
            'receiver_decided_at': transfer.receiver_decided_at.isoformat() if transfer.receiver_decided_at else None,
            'admin_decision': transfer.admin_decision,
            'admin_comment': transfer.admin_comment,
            'admin_decided_at': transfer.admin_decided_at.isoformat() if transfer.admin_decided_at else None,
            'approved_by': {
                'id': transfer.approved_by.pk,
                'name': transfer.approved_by.get_full_name() or transfer.approved_by.username,
            } if transfer.approved_by else None,
            'created_at': transfer.created_at.isoformat(),
            'updated_at': transfer.updated_at.isoformat(),
        })
    
    return JsonResponse({
        'success': True,
        'transfers': transfers_data,
        'count': len(transfers_data),
    })


@api_login_required
@require_http_methods(["POST"])
def api_category_update(request, category_id):
    """
    WORLD-CLASS: Update category name and description - Admin only
    
    CSRF Protection: Provided by CsrfViewMiddleware (global)
    """
    from assets.models import AssetCategory
    from audit.models import AuditLog
    
    # Enforce admin-only access
    if not can(request.user, "manage_categories"):
        return _json_error("Permission denied. Admin access required.", status=403)
    
    company = _company_from_request(request)
    if not company:
        return _json_error("Company context required.", status=403)
    
    try:
        category = AssetCategory.objects.for_company(company).get(pk=category_id)
    except AssetCategory.DoesNotExist:
        return _json_error("Category not found.", status=404)
    
    try:
        data = _parse_body(request)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return _json_error("Category name is required.")
        
        # Check for duplicate name (excluding current category)
        if AssetCategory.objects.for_company(company).exclude(pk=category_id).filter(name=name).exists():
            return _json_error(f"Category with name '{name}' already exists.")
        
        old_name = category.name
        old_description = category.description
        category.name = name
        category.description = description
        category.save()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            company=company,
            action='update',
            details=f"Updated category from '{old_name}' to '{name}'",
            metadata={
                'model': 'AssetCategory',
                'category_id': category.id,
                'old_name': old_name,
                'new_name': name,
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Category updated successfully',
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
            }
        })
        
    except ValidationError as e:
        return _json_error(str(e))
    except Exception as e:
        return _json_error(f"Failed to update category: {str(e)}", status=500)


@api_login_required
@require_http_methods(["POST"])
def api_category_delete(request, category_id):
    """
    WORLD-CLASS: Delete category - Admin only. Prevents deletion if assets exist.
    
    CSRF Protection: Provided by CsrfViewMiddleware (global)
    """
    from assets.models import AssetCategory, Asset
    from audit.models import AuditLog
    
    # Enforce admin-only access
    if not can(request.user, "manage_categories"):
        return _json_error("Permission denied. Admin access required.", status=403)
    
    company = _company_from_request(request)
    if not company:
        return _json_error("Company context required.", status=403)
    
    try:
        category = AssetCategory.objects.for_company(company).get(pk=category_id)
    except AssetCategory.DoesNotExist:
        return _json_error("Category not found.", status=404)
    
    # Check if category has assets
    asset_count = Asset.objects.for_company(company).filter(category=category).count()
    if asset_count > 0:
        return _json_error(
            f"Cannot delete category. {asset_count} asset(s) are using this category. "
            "Please reassign or delete those assets first.",
            status=400
        )
    
    try:
        category_name = category.name
        category.delete()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            company=company,
            action='delete',
            target_model='AssetCategory',
            target_id=str(category_id),
            details=f"Deleted category '{category_name}'"
        )
        
        return JsonResponse({
            'success': True,
            'message': f"Category '{category_name}' deleted successfully"
        })
        
    except Exception as e:
        return _json_error(f"Failed to delete category: {str(e)}", status=500)


__all__ = [
    "api_transfer_initiate",
    "api_transfer_receiver_decision",
    "api_transfer_admin_review",
    "api_transfer_alerts",
    "api_transfer_list",
    "api_category_fields_enhanced",
    "api_category_update",
    "api_category_delete",
]
