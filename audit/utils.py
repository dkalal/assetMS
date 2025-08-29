from audit.models import AuditLog

# Action constants for audit logging
ASSIGN_ACTION = 'assign'
MAINTENANCE_ACTION = 'maintenance'
SCAN_ACTION = 'scan'

def log_audit(user, action, asset=None, details='', related_user=None, related_asset=None, metadata=None):
    AuditLog.objects.create(
        user=user,
        action=action,
        asset=asset,
        details=details,
        related_user=related_user,
        related_asset=related_asset,
        metadata=metadata or {},
    ) 