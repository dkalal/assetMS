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
