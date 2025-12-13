from typing import Optional
from decimal import Decimal
from django.utils import timezone

from audit.models import AuditLog, AuditEvent

# ============================================================================
# AUDIT ACTION CONSTANTS
# World-Class Audit Trail (ServiceNow ITAM, IBM Maximo, SAP EAM)
# ============================================================================

# Asset Lifecycle Actions
ASSET_ACTION = 'asset'  # Generic asset action (create, update, delete)
CREATE_ACTION = 'create'  # Asset/record creation
UPDATE_ACTION = 'update'  # Asset/record update
DELETE_ACTION = 'delete'  # Asset/record deletion
ASSIGN_ACTION = 'assign'  # Asset assignment to user
TRANSFER_ACTION = 'transfer'  # Asset transfer between branches

# Maintenance Actions
MAINTENANCE_ACTION = 'maintenance'  # Maintenance operations

# Asset Tracking Actions
SCAN_ACTION = 'scan'  # QR code scan
CHECKIN_ACTION = 'checkin'  # Asset check-in
CHECKOUT_ACTION = 'checkout'  # Asset check-out

# Authentication Actions
LOGIN_ACTION = 'login'  # Successful login
LOGOUT_ACTION = 'logout'  # User logout
LOGIN_FAILED_ACTION = 'login_failed'  # Failed login attempt
ACCOUNT_LOCKED_ACTION = 'account_locked'  # Account lockout

# Approval Actions
APPROVAL_ACTION = 'approval'  # Approval request/decision
REJECT_ACTION = 'reject'  # Rejection decision

# Bulk Operations
BULK_IMPORT_ACTION = 'bulk_import'  # Bulk import operation
BULK_EXPORT_ACTION = 'bulk_export'  # Bulk export operation
BULK_UPDATE_ACTION = 'bulk_update'  # Bulk update operation


def _serialize_metadata(metadata: Optional[dict]) -> dict:
    """
    Convert metadata values to JSON-serializable types.
    Handles Decimal, UUID, and other non-serializable types.
    """
    if not metadata:
        return {}
    
    serialized = {}
    for key, value in metadata.items():
        if isinstance(value, Decimal):
            # Convert Decimal to string to preserve precision
            serialized[key] = str(value)
        elif hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, list, dict, type(None))):
            # Convert other non-serializable types to string
            serialized[key] = str(value)
        else:
            serialized[key] = value
    
    return serialized


def log_audit(
    user,
    action: str,
    asset=None,
    details: str = '',
    *,
    company=None,
    branch=None,
    related_user=None,
    related_asset=None,
    metadata: Optional[dict] = None,
):
    """Persist a tenancy-aware audit entry with safe fallbacks."""

    company = company or getattr(asset, 'company', None) or getattr(user, 'company', None)
    if branch is None:
        branch = getattr(asset, 'branch', None)
        if branch is None:
            branch = getattr(getattr(user, 'primary_branch_membership', None), 'branch', None)
            if branch is None:
                branch = getattr(user, 'primary_branch', None)

    # Serialize metadata to ensure JSON compatibility
    safe_metadata = _serialize_metadata(metadata)

    AuditLog.objects.create(
        user=user,
        action=action,
        asset=asset,
        details=details,
        company=company,
        branch=branch,
        related_user=related_user,
        related_asset=related_asset,
        metadata=safe_metadata,
    )


# ============================================================================
# Authentication Audit Logging Functions
# Following world-class standards: ServiceNow ITAM, IBM Maximo, SAP EAM
# ============================================================================

def get_client_ip(request):
    """
    Extract client IP address from request.
    Handles proxy headers (X-Forwarded-For) for accurate tracking.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip


def log_login_success(user, request):
    """
    Log successful login event.
    
    Captures:
    - User who logged in
    - Timestamp (automatic)
    - IP address
    - User agent
    - Company/Branch context
    
    Args:
        user: User instance who logged in
        request: HttpRequest object
    """
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    
    # Get company and branch from user
    company = getattr(user, 'company', None)
    branch = getattr(user, 'primary_branch', None)
    
    details = f"User '{user.username}' logged in successfully from {ip_address}"
    
    metadata = {
        'ip_address': ip_address,
        'user_agent': user_agent,
        'session_key': request.session.session_key if hasattr(request, 'session') else None,
    }
    
    log_audit(
        user=user,
        action=LOGIN_ACTION,
        details=details,
        company=company,
        branch=branch,
        metadata=metadata
    )


def log_login_failure(username, request, reason='Invalid credentials'):
    """
    Log failed login attempt.
    
    Captures:
    - Username attempted
    - Timestamp (automatic)
    - IP address
    - Failure reason
    - User agent
    
    Args:
        username: Username that was attempted
        request: HttpRequest object
        reason: Reason for failure (default: 'Invalid credentials')
    
    Note: User is None since login failed
    """
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    
    details = f"Failed login attempt for username '{username}' from {ip_address}. Reason: {reason}"
    
    metadata = {
        'ip_address': ip_address,
        'user_agent': user_agent,
        'username_attempted': username,
        'failure_reason': reason,
    }
    
    # Create audit log without user (since login failed)
    AuditLog.objects.create(
        user=None,
        action=LOGIN_FAILED_ACTION,
        details=details,
        company=None,
        branch=None,
        metadata=metadata,
    )


def log_logout(user, request, session_duration=None):
    """
    Log logout event.
    
    Captures:
    - User who logged out
    - Timestamp (automatic)
    - Session duration (if available)
    - IP address
    
    Args:
        user: User instance who logged out
        request: HttpRequest object
        session_duration: Duration of session in seconds (optional)
    """
    ip_address = get_client_ip(request)
    
    # Get company and branch from user
    company = getattr(user, 'company', None)
    branch = getattr(user, 'primary_branch', None)
    
    details = f"User '{user.username}' logged out from {ip_address}"
    if session_duration:
        details += f" (session duration: {session_duration:.0f} seconds)"
    
    metadata = {
        'ip_address': ip_address,
        'session_duration': session_duration,
    }
    
    log_audit(
        user=user,
        action=LOGOUT_ACTION,
        details=details,
        company=company,
        branch=branch,
        metadata=metadata
    )


def log_account_lockout(user, request, failed_attempts):
    """
    Log account lockout event.
    
    Captures:
    - User whose account was locked
    - Number of failed attempts
    - Timestamp (automatic)
    - IP address
    
    Args:
        user: User instance whose account was locked
        request: HttpRequest object
        failed_attempts: Number of failed login attempts
    """
    ip_address = get_client_ip(request)
    
    # Get company and branch from user
    company = getattr(user, 'company', None)
    branch = getattr(user, 'primary_branch', None)
    
    details = f"Account '{user.username}' locked after {failed_attempts} failed login attempts from {ip_address}"
    
    metadata = {
        'ip_address': ip_address,
        'failed_attempts': failed_attempts,
        'locked_until': str(user.account_locked_until) if hasattr(user, 'account_locked_until') and user.account_locked_until else None,
    }
    
    log_audit(
        user=user,
        action=ACCOUNT_LOCKED_ACTION,
        details=details,
        company=company,
        branch=branch,
        metadata=metadata
    )


def log_password_reset_requested(user, request, identifier: str, success: bool, target_user=None):
    """Log password reset request using the enterprise AuditEvent model.

    Captures:
    - Identifier used (email or username)
    - Whether a matching account was found and email queued
    - Tenant context (company)
    - IP address and user agent
    - Requesting user (if authenticated) and target user (if resolved)
    """

    # Derive network context
    ip_address = get_client_ip(request) if request is not None else None
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown') if request is not None else 'unknown'

    # Resolve company with robust fallbacks: target user -> requesting user -> request.company
    company = None
    if target_user is not None and getattr(target_user, 'company', None) is not None:
        company = target_user.company
    elif user is not None and getattr(user, 'company', None) is not None:
        company = user.company
    elif request is not None and getattr(request, 'user', None) is not None and getattr(request.user, 'company', None) is not None:
        company = request.user.company
    elif request is not None and getattr(request, 'company', None) is not None:
        company = request.company

    # If we still cannot determine company, skip event to avoid breaking the flow
    if company is None:
        return

    description_status = 'link sent' if success else 'no matching account'
    description = f"Password reset request for identifier '{identifier}' - {description_status}"

    metadata = {
        'identifier': identifier,
        'success': success,
        'ip_address': ip_address,
        'target_user_id': getattr(target_user, 'id', None),
        'request_user_id': getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None,
    }

    AuditEvent.log_event(
        company=company,
        action='PASSWORD_RESET',
        user=user if getattr(user, 'is_authenticated', False) else None,
        severity='INFO' if success else 'WARNING',
        description=description,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
        related_user=target_user,
    )