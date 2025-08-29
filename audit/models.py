from django.db import models
from django.conf import settings
from assets.models import Asset

# Create your models here.

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('view', 'View'),
        ('edit', 'Edit'),
        ('move', 'Move'),
        ('delete', 'Delete'),
        ('create', 'Create'),
        ('add', 'Add'),
        ('assign', 'Assign/Transfer'),
        ('scan', 'Scan'),
        ('maintenance', 'Maintenance'),
        ('error', 'Error'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    # Enterprise enhancements
    related_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='related_audit_logs')
    related_asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name='related_audit_logs')
    metadata = models.JSONField(default=dict, blank=True, help_text="Structured metadata for advanced filtering/grouping")

    def __str__(self):
        return f"{self.user} {self.action} {self.asset} at {self.timestamp}"
