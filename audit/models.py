from django.conf import settings
from django.db import models

from assets.models import Asset


class AuditLog(models.Model):
    """Enterprise audit record scoped by company and branch."""

    ACTION_CHOICES = [
        ("view", "View"),
        ("edit", "Edit"),
        ("move", "Move"),
        ("delete", "Delete"),
        ("create", "Create"),
        ("add", "Add"),
        ("assign", "Assign/Transfer"),
        ("scan", "Scan"),
        ("maintenance", "Maintenance"),
        ("error", "Error"),
        ("login", "Login"),
        ("logout", "Logout"),
    ]

    company = models.ForeignKey(
        "tenancy.Company",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
        help_text="Owning company for tenancy scoping.",
    )
    branch = models.ForeignKey(
        "tenancy.Branch",
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
        help_text="Branch context when applicable.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    # Enterprise enhancements
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_audit_logs",
    )
    related_asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_audit_logs",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured metadata for advanced filtering/grouping",
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["company", "branch", "timestamp"], name="audit_company_branch_ts"),
            models.Index(fields=["action", "timestamp"], name="audit_action_ts"),
        ]

    def __str__(self):
        return f"{self.user} {self.action} {self.asset} at {self.timestamp}"


class AuditEvent(models.Model):
    """
    Enterprise audit event model for logging system-wide events.
    Tracks user actions, security events, and system changes.
    Required by workspace coding rules for audit trail.
    """
    
    EVENT_TYPES = [
        # User Management
        ('USER_CREATED', 'User Created'),
        ('USER_UPDATED', 'User Updated'),
        ('USER_DELETED', 'User Deleted'),
        ('USER_ACTIVATED', 'User Activated'),
        ('USER_DEACTIVATED', 'User Deactivated'),
        ('PASSWORD_CHANGED', 'Password Changed'),
        ('PASSWORD_RESET', 'Password Reset'),
        
        # Authentication
        ('LOGIN_SUCCESS', 'Login Success'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('LOGOUT', 'Logout'),
        ('SESSION_EXPIRED', 'Session Expired'),
        
        # Asset Management
        ('ASSET_CREATED', 'Asset Created'),
        ('ASSET_UPDATED', 'Asset Updated'),
        ('ASSET_DELETED', 'Asset Deleted'),
        ('ASSET_TRANSFERRED', 'Asset Transferred'),
        ('ASSET_STATUS_CHANGED', 'Asset Status Changed'),
        
        # System Events
        ('SETTINGS_CHANGED', 'Settings Changed'),
        ('PERMISSION_CHANGED', 'Permission Changed'),
        ('BACKUP_CREATED', 'Backup Created'),
        ('BACKUP_RESTORED', 'Backup Restored'),
    ]
    
    SEVERITY_LEVELS = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Core fields
    company = models.ForeignKey(
        'tenancy.Company',
        on_delete=models.CASCADE,
        related_name='audit_events',
        help_text='Company context for multi-tenancy'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events',
        help_text='User who performed the action'
    )
    action = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        db_index=True,
        help_text='Type of event/action'
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='INFO',
        db_index=True,
        help_text='Severity level of the event'
    )
    
    # Event details
    description = models.TextField(
        blank=True,
        help_text='Human-readable description of the event'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional structured data about the event'
    )
    
    # Context
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the user'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='Browser/client user agent'
    )
    
    # Related objects
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_audit_events',
        help_text='User affected by the action (e.g., user being edited)'
    )
    related_asset = models.ForeignKey(
        'assets.Asset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events',
        help_text='Asset related to the action'
    )
    
    # Timestamps
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the event occurred'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['company', 'timestamp'], name='audit_evt_company_ts'),
            models.Index(fields=['action', 'timestamp'], name='audit_evt_action_ts'),
            models.Index(fields=['user', 'timestamp'], name='audit_evt_user_ts'),
            models.Index(fields=['severity', 'timestamp'], name='audit_evt_severity_ts'),
        ]
        verbose_name = 'Audit Event'
        verbose_name_plural = 'Audit Events'
    
    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"{user_str} - {self.get_action_display()} at {self.timestamp}"
    
    @classmethod
    def log_event(cls, company, action, user=None, severity='INFO', description='', 
                  metadata=None, ip_address=None, user_agent=None, 
                  related_user=None, related_asset=None):
        """
        Convenience method to create audit events.
        
        Usage:
            AuditEvent.log_event(
                company=request.user.company,
                action='USER_UPDATED',
                user=request.user,
                description='Updated user profile',
                metadata={'user_id': user.id, 'changes': {...}}
            )
        """
        return cls.objects.create(
            company=company,
            user=user,
            action=action,
            severity=severity,
            description=description,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            related_user=related_user,
            related_asset=related_asset
        )
