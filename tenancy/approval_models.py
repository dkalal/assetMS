"""
Approval Workflow Models

Provides a flexible approval system for various actions requiring manager/admin approval.
Supports multi-level approvals, escalation, and comprehensive audit trails.
"""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from tenancy.models import Branch, Company, CompanyScopedModel


class ApprovalRequest(CompanyScopedModel):
    """
    Represents a request that requires approval from a manager or admin.
    
    Supports various request types:
    - Asset transfers
    - Asset maintenance
    - Asset disposal
    - User access requests
    - Budget approvals
    - Custom workflows
    
    Features:
    - Multi-level approval chains
    - Automatic escalation
    - Approval history tracking
    - Notification system
    - Deadline management
    """
    
    # Request Types (Simplified - Option 2)
    TYPE_ASSET_CREATION = 'asset_creation'
    TYPE_ASSET_DISPOSAL = 'asset_disposal'
    TYPE_ASSET_TRANSFER = 'asset_transfer'
    TYPE_ASSET_MAINTENANCE = 'asset_maintenance'
    TYPE_USER_ACCESS = 'user_access'
    TYPE_BUDGET = 'budget'
    TYPE_CUSTOM = 'custom'
    
    REQUEST_TYPES = [
        (TYPE_ASSET_CREATION, 'Asset Creation'),
        (TYPE_ASSET_DISPOSAL, 'Asset Disposal'),
        (TYPE_ASSET_TRANSFER, 'Asset Transfer'),
        (TYPE_ASSET_MAINTENANCE, 'Asset Maintenance'),
        (TYPE_USER_ACCESS, 'User Access Request'),
        (TYPE_BUDGET, 'Budget Approval'),
        (TYPE_CUSTOM, 'Custom Request'),
    ]
    
    # Status
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    STATUS_ESCALATED = 'escalated'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_ESCALATED, 'Escalated'),
    ]
    
    # Priority
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]
    
    # Fields
    request_type = models.CharField(
        max_length=50,
        choices=REQUEST_TYPES,
        help_text="Type of approval request"
    )
    
    title = models.CharField(
        max_length=255,
        help_text="Brief title of the request"
    )
    
    description = models.TextField(
        help_text="Detailed description of the request"
    )
    
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='approval_requests',
        help_text="Branch where request originated"
    )
    
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='approval_requests_created',
        help_text="User who created the request"
    )
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_requests_assigned',
        help_text="Manager/admin assigned to review"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM
    )
    
    # Approval details
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_requests_approved'
    )
    
    approved_at = models.DateTimeField(null=True, blank=True)
    
    rejection_reason = models.TextField(blank=True)
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data specific to request type"
    )
    
    # Deadlines
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Deadline for approval decision"
    )
    
    escalated_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status', 'created_at']),
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_request_type_display()}: {self.title} ({self.get_status_display()})"
    
    def clean(self):
        """Validate approval request."""
        super().clean()
        
        # Validate assigned_to belongs to company
        if self.assigned_to:
            if not hasattr(self.assigned_to, 'company') or self.assigned_to.company != self.company:
                raise ValidationError("Assigned user must belong to the same company.")
            
            # Validate assigned_to has appropriate role
            if hasattr(self.assigned_to, 'role'):
                valid_roles = ['admin', 'manager']
                if self.assigned_to.role not in valid_roles:
                    raise ValidationError("Assigned user must have manager or admin role.")
    
    def approve(self, approved_by, notes: str = None):
        """
        Approve the request.
        
        Args:
            approved_by: User approving the request
            notes: Optional approval notes
        """
        with transaction.atomic():
            self.status = self.STATUS_APPROVED
            self.approved_by = approved_by
            self.approved_at = timezone.now()
            
            if notes:
                if 'approval_notes' not in self.metadata:
                    self.metadata['approval_notes'] = []
                self.metadata['approval_notes'].append({
                    'approved_by': approved_by.username,
                    'approved_at': timezone.now().isoformat(),
                    'notes': notes,
                })
            
            self.save()
            
            # Create notification for requester
            from tenancy.models import Alert
            Alert.objects.create(
                company=self.company,
                branch=self.branch,
                recipient=self.requested_by,
                level=Alert.LEVEL_SUCCESS,
                message=f"Your request '{self.title}' has been approved by {approved_by.get_full_name() or approved_by.username}.",
                context={
                    'request_id': self.pk,
                    'request_type': self.request_type,
                    'approved_by': approved_by.pk,
                    'approved_at': timezone.now().isoformat(),
                }
            )
            
            # Log audit event
            from audit.utils import log_audit
            log_audit(
                approved_by,
                "approval_request_approved",
                details=f"Approved request: {self.title}",
                company=self.company,
                branch=self.branch,
                related_user=self.requested_by,
                metadata={
                    'request_id': self.pk,
                    'request_type': self.request_type,
                    'title': self.title,
                }
            )
    
    def reject(self, rejected_by, reason: str):
        """
        Reject the request.
        
        Args:
            rejected_by: User rejecting the request
            reason: Reason for rejection
        """
        with transaction.atomic():
            self.status = self.STATUS_REJECTED
            self.approved_by = rejected_by  # Store who made the decision
            self.approved_at = timezone.now()
            self.rejection_reason = reason
            self.save()
            
            # Create notification for requester
            from tenancy.models import Alert
            Alert.objects.create(
                company=self.company,
                branch=self.branch,
                recipient=self.requested_by,
                level=Alert.LEVEL_WARNING,
                message=f"Your request '{self.title}' has been rejected. Reason: {reason}",
                context={
                    'request_id': self.pk,
                    'request_type': self.request_type,
                    'rejected_by': rejected_by.pk,
                    'reason': reason,
                }
            )
            
            # Log audit event
            from audit.utils import log_audit
            log_audit(
                rejected_by,
                "approval_request_rejected",
                details=f"Rejected request: {self.title}. Reason: {reason}",
                company=self.company,
                branch=self.branch,
                related_user=self.requested_by,
                metadata={
                    'request_id': self.pk,
                    'request_type': self.request_type,
                    'title': self.title,
                    'reason': reason,
                }
            )
    
    def escalate(self):
        """Escalate the request to a higher authority."""
        with transaction.atomic():
            self.status = self.STATUS_ESCALATED
            self.escalated_at = timezone.now()
            self.save()
            
            # Find admin to escalate to
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin = User.objects.filter(
                company=self.company,
                role='admin',
                is_active=True
            ).first()
            
            if admin:
                self.assigned_to = admin
                self.save()
                
                # Notify admin
                from tenancy.models import Alert
                Alert.objects.create(
                    company=self.company,
                    branch=self.branch,
                    recipient=admin,
                    level=Alert.LEVEL_WARNING,
                    message=f"Request '{self.title}' has been escalated to you for review.",
                    context={
                        'request_id': self.pk,
                        'request_type': self.request_type,
                        'escalated_at': timezone.now().isoformat(),
                    }
                )
    
    @property
    def is_overdue(self) -> bool:
        """Check if request is past deadline."""
        if self.deadline and self.status == self.STATUS_PENDING:
            return timezone.now() > self.deadline
        return False
    
    @property
    def response_time_hours(self) -> float:
        """Calculate response time in hours."""
        if self.approved_at:
            delta = self.approved_at - self.created_at
            return delta.total_seconds() / 3600
        return 0.0
    
    def create_asset_from_approval(self):
        """Create asset from approved asset creation request."""
        if self.request_type != self.TYPE_ASSET_CREATION:
            raise ValidationError("This method only applies to asset creation requests.")
        
        if self.status != self.STATUS_APPROVED:
            raise ValidationError("Request must be approved before creating asset.")
        
        asset_data = self.metadata.get('asset_data', {})
        if not asset_data:
            raise ValidationError("No asset data found in request metadata.")
        
        # Import here to avoid circular dependency
        from assets.models import Asset, AssetCategory
        
        with transaction.atomic():
            # Validate category
            category_id = asset_data.get('category_id')
            try:
                category = AssetCategory.objects.for_company(self.company).get(pk=category_id)
            except AssetCategory.DoesNotExist:
                raise ValidationError(f"Category {category_id} not found.")
            
            # Validate branch
            branch_id = asset_data.get('branch_id')
            if branch_id:
                try:
                    branch = Branch.objects.get(pk=branch_id, company=self.company)
                except Branch.DoesNotExist:
                    raise ValidationError(f"Branch {branch_id} not found or doesn't belong to company.")
            else:
                branch = self.branch
            
            # Create asset
            asset = Asset.objects.create(
                company=self.company,
                branch=branch,
                category=category,
                description=asset_data.get('description', ''),
                status=asset_data.get('status', Asset.STATUS_ACTIVE),
                dynamic_data=asset_data.get('dynamic_data', {}),
                assigned_to_id=asset_data.get('assigned_to_id'),
            )
            
            # Generate QR code
            try:
                import qrcode
                from io import BytesIO
                from django.core.files.base import ContentFile
                import os
                from django.conf import settings
                
                qr_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
                os.makedirs(qr_dir, exist_ok=True)
                
                # Use the approved_by user's request for URL building
                # Fallback to a default base URL if no request available
                base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
                qr_url = f"{base_url}/assets/{asset.uuid}/"
                qr = qrcode.make(qr_url)
                buffer = BytesIO()
                qr.save(buffer, 'PNG')
                asset.qr_code.save(f"asset_{asset.uuid}.png", ContentFile(buffer.getvalue()), save=False)
                asset.save()
            except Exception as e:
                # Log but don't fail if QR generation fails
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"QR code generation failed for asset {asset.uuid}: {e}")
            
            # Store asset reference in metadata
            self.metadata['created_asset_id'] = asset.id
            self.metadata['created_asset_uuid'] = str(asset.uuid)
            self.save()
            
            # Log audit event
            from audit.utils import log_audit
            log_audit(
                self.approved_by,
                "asset_created_from_approval",
                asset,
                f"Asset created from approved request: {self.title}",
                company=self.company,
                branch=branch,
                metadata={
                    'request_id': self.pk,
                    'requested_by': self.requested_by.username,
                    'approved_by': self.approved_by.username,
                }
            )
            
            # Notify requester
            from tenancy.models import Alert
            Alert.objects.create(
                company=self.company,
                branch=self.branch,
                recipient=self.requested_by,
                level=Alert.LEVEL_SUCCESS,
                message=f"Your asset creation request '{self.title}' has been approved and the asset has been created.",
                context={
                    'request_id': self.pk,
                    'asset_id': asset.id,
                    'asset_uuid': str(asset.uuid),
                }
            )
            
            return asset
    
    def execute_asset_disposal(self):
        """Execute asset disposal from approved disposal request."""
        if self.request_type != self.TYPE_ASSET_DISPOSAL:
            raise ValidationError("This method only applies to asset disposal requests.")
        
        if self.status != self.STATUS_APPROVED:
            raise ValidationError("Request must be approved before disposing asset.")
        
        asset_id = self.metadata.get('asset_id')
        if not asset_id:
            raise ValidationError("No asset ID found in request metadata.")
        
        # Import here to avoid circular dependency
        from assets.models import Asset
        
        with transaction.atomic():
            try:
                asset = Asset.objects.get(id=asset_id, company=self.company)
            except Asset.DoesNotExist:
                raise ValidationError(f"Asset {asset_id} not found or doesn't belong to company.")
            
            # Get disposal details from metadata
            disposal_reason = self.metadata.get('disposal_reason', self.description)
            disposal_method = self.metadata.get('disposal_method', 'retired')
            
            # Update asset status
            old_status = asset.status
            if disposal_method == 'retired':
                asset.status = Asset.STATUS_RETIRED
            elif disposal_method == 'lost':
                asset.status = Asset.STATUS_LOST
            elif disposal_method == 'deleted':
                asset.status = Asset.STATUS_DELETED
            else:
                asset.status = Asset.STATUS_RETIRED  # Default
            
            asset.save()
            
            # Store disposal reference in metadata
            self.metadata['disposed_at'] = timezone.now().isoformat()
            self.metadata['old_status'] = old_status
            self.metadata['new_status'] = asset.status
            self.save()
            
            # Log audit event
            from audit.utils import log_audit
            log_audit(
                self.approved_by,
                "asset_disposed_from_approval",
                asset,
                f"Asset disposed from approved request: {self.title}. Reason: {disposal_reason}",
                company=self.company,
                branch=asset.branch,
                metadata={
                    'request_id': self.pk,
                    'requested_by': self.requested_by.username,
                    'approved_by': self.approved_by.username,
                    'disposal_reason': disposal_reason,
                    'disposal_method': disposal_method,
                    'old_status': old_status,
                    'new_status': asset.status,
                }
            )
            
            # Notify requester
            from tenancy.models import Alert
            Alert.objects.create(
                company=self.company,
                branch=self.branch,
                recipient=self.requested_by,
                level=Alert.LEVEL_SUCCESS,
                message=f"Your asset disposal request '{self.title}' has been approved and the asset has been disposed.",
                context={
                    'request_id': self.pk,
                    'asset_id': asset.id,
                    'asset_uuid': str(asset.uuid),
                    'disposal_method': disposal_method,
                }
            )
            
            return asset
