from typing import Optional
from decimal import Decimal

from audit.models import AuditLog

# Action constants for audit logging
ASSIGN_ACTION = 'assign'
MAINTENANCE_ACTION = 'maintenance'
SCAN_ACTION = 'scan'


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