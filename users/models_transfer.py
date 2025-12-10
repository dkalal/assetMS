# users/models_transfer.py
"""
User Branch Transfer Models

WORLD-CLASS: Hybrid approach combining Technique 3 (Retention + Unassign) 
and Technique 5 (Manual Selection) with admin/manager approval workflow.

Inspired by:
- ServiceNow ITAM: Multi-step approval workflow
- IBM Maximo: Asset transfer requests
- SAP EAM: Equipment transfer with authorization
- Oracle EBS: Asset requisitions

Architecture:
- UserBranchTransferRequest: Main workflow tracker
- AssetTransferSelection: Individual asset selection tracking
- Complete state machine for workflow
- Multi-tenancy enforcement
- Comprehensive audit trail
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Index, Q
from django.utils import timezone

from tenancy.models import Branch, Company


class UserBranchTransferRequest(models.Model):
    """
    Central model for user branch transfer workflow.
    
    Workflow States:
    1. pending_user_selection: User needs to select assets
    2. pending_approval: Admin/Manager needs to approve
    3. approved: Approved, ready for execution
    4. completed: Successfully executed
    5. rejected: Rejected by approver
    6. cancelled: Cancelled by initiator
    
    Multi-Tenancy: Enforced via company foreign key
    Security: Role-based permissions checked in service layer
    """
    
    # Status constants
    STATUS_PENDING_MANAGER_APPROVAL = 'pending_manager_approval'
    STATUS_PENDING_USER_SELECTION = 'pending_user_selection'
    STATUS_PENDING_APPROVAL = 'pending_approval'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_PENDING_MANAGER_APPROVAL, 'Pending Manager Approval'),
        (STATUS_PENDING_USER_SELECTION, 'Pending User Selection'),
        (STATUS_PENDING_APPROVAL, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    # Initiation type constants
    INITIATION_TYPE_ADMIN = 'admin_initiated'
    INITIATION_TYPE_USER = 'user_initiated'
    
    INITIATION_TYPE_CHOICES = [
        (INITIATION_TYPE_ADMIN, 'Admin Initiated'),
        (INITIATION_TYPE_USER, 'User Initiated'),
    ]
    
    # Active states (can still be modified)
    ACTIVE_STATES = [STATUS_PENDING_MANAGER_APPROVAL, STATUS_PENDING_USER_SELECTION, STATUS_PENDING_APPROVAL, STATUS_APPROVED]
    
    # Final states (cannot be modified)
    FINAL_STATES = [STATUS_COMPLETED, STATUS_REJECTED, STATUS_CANCELLED]
    
    # Core relationships
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='user_transfer_requests',
        help_text='Company context for multi-tenancy'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transfer_requests',
        help_text='User being transferred'
    )
    
    # Branch transfer
    from_branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='outgoing_user_transfers',
        help_text='Original branch (can be null if user had no branch)'
    )
    
    to_branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='incoming_user_transfers',
        help_text='Destination branch'
    )
    
    # Workflow status
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING_USER_SELECTION,
        db_index=True,
        help_text='Current workflow status'
    )
    
    # Initiation type
    initiation_type = models.CharField(
        max_length=20,
        choices=INITIATION_TYPE_CHOICES,
        default=INITIATION_TYPE_ADMIN,
        help_text='Who initiated this transfer request'
    )
    
    # Actors
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_user_transfers',
        help_text='Admin/Manager/User who initiated transfer'
    )
    
    manager_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manager_approved_user_transfers',
        help_text='Manager who approved user-initiated transfer'
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_user_transfers',
        help_text='Admin who approved transfer'
    )
    
    # Reasons and notes
    initiation_reason = models.TextField(
        help_text='Reason for initiating transfer (e.g., "Employee relocation")'
    )
    
    user_selection_notes = models.TextField(
        blank=True,
        help_text='Optional notes from user about their selections'
    )
    
    manager_approval_reason = models.TextField(
        blank=True,
        help_text='Manager approval/rejection reason'
    )
    
    approval_reason = models.TextField(
        blank=True,
        help_text='Admin approval decision reason'
    )
    
    rejection_reason = models.TextField(
        blank=True,
        help_text='Reason for rejection'
    )
    
    # Timestamps
    initiated_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When transfer was initiated'
    )
    
    user_selection_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When user submitted asset selections'
    )
    
    manager_approval_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When manager approved the request'
    )
    
    approval_decision_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When admin made approval decision'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When transfer was fully executed'
    )
    
    # Statistics (denormalized for performance)
    total_assets = models.PositiveIntegerField(
        default=0,
        help_text='Total number of assets user had at initiation'
    )
    
    assets_selected_by_user = models.PositiveIntegerField(
        default=0,
        help_text='Number of assets user selected to transfer'
    )
    
    assets_approved = models.PositiveIntegerField(
        default=0,
        help_text='Number of assets approved by admin'
    )
    
    assets_transferred = models.PositiveIntegerField(
        default=0,
        help_text='Number of assets successfully transferred'
    )
    
    assets_unassigned = models.PositiveIntegerField(
        default=0,
        help_text='Number of assets successfully unassigned'
    )
    
    # Metadata for extensibility
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional metadata (e.g., HR ticket number, effective date)'
    )
    
    class Meta:
        db_table = 'user_branch_transfer_requests'
        verbose_name = 'User Branch Transfer Request'
        verbose_name_plural = 'User Branch Transfer Requests'
        ordering = ['-initiated_at']
        
        indexes = [
            Index(fields=['company', 'status']),
            Index(fields=['user', 'status']),
            Index(fields=['to_branch', 'status']),
            Index(fields=['initiated_at']),
            Index(fields=['status', 'initiated_at']),
        ]
        
        constraints = [
            # Ensure only one active transfer per user per company
            models.UniqueConstraint(
                fields=['user', 'company'],
                condition=Q(status__in=['pending_user_selection', 'pending_approval', 'approved']),
                name='unique_active_transfer_per_user'
            ),
        ]
    
    def __str__(self):
        return f"Transfer: {self.user.username} → {self.to_branch.name} ({self.get_status_display()})"
    
    def clean(self):
        """Validate model constraints"""
        super().clean()
        
        # Validate company consistency
        if self.user.company_id != self.company_id:
            raise ValidationError("User must belong to the same company as the transfer request")
        
        if self.to_branch.company_id != self.company_id:
            raise ValidationError("Destination branch must belong to the same company")
        
        if self.from_branch and self.from_branch.company_id != self.company_id:
            raise ValidationError("Source branch must belong to the same company")
        
        # Validate branch change
        if self.from_branch and self.from_branch_id == self.to_branch_id:
            raise ValidationError("Source and destination branches cannot be the same")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        """Check if transfer is in active state"""
        return self.status in self.ACTIVE_STATES
    
    @property
    def is_final(self):
        """Check if transfer is in final state"""
        return self.status in self.FINAL_STATES
    
    @property
    def can_user_select_assets(self):
        """Check if user can select assets"""
        return self.status == self.STATUS_PENDING_USER_SELECTION
    
    @property
    def can_be_approved(self):
        """Check if transfer can be approved"""
        return self.status == self.STATUS_PENDING_APPROVAL
    
    @property
    def can_be_executed(self):
        """Check if transfer can be executed"""
        return self.status == self.STATUS_APPROVED
    
    def get_selected_assets(self):
        """Get assets selected by user for transfer"""
        return self.asset_selections.filter(selected_by_user=True)
    
    def get_approved_assets(self):
        """Get assets approved by admin for transfer"""
        return self.asset_selections.filter(
            selected_by_user=True,
            approved_by_admin=True
        )
    
    def get_unselected_assets(self):
        """Get assets not selected by user (will be unassigned)"""
        return self.asset_selections.filter(selected_by_user=False)


class AssetTransferSelection(models.Model):
    """
    Tracks individual asset selections within a transfer request.
    
    Each record represents one asset that the user can choose to transfer or leave behind.
    
    Selection Flow:
    1. Created when transfer initiated (all user's assets)
    2. User selects/deselects assets
    3. Admin approves/rejects each selection
    4. System executes transfer or unassignment
    
    Multi-Tenancy: Enforced via company foreign key
    """
    
    # Status constants
    STATUS_NOT_SELECTED = 'not_selected'      # Default, will be unassigned
    STATUS_SELECTED = 'selected'              # User selected to transfer
    STATUS_APPROVED = 'approved'              # Admin approved transfer
    STATUS_REJECTED = 'rejected'              # Admin rejected transfer
    STATUS_TRANSFERRED = 'transferred'        # Successfully transferred
    STATUS_UNASSIGNED = 'unassigned'          # Successfully unassigned
    
    STATUS_CHOICES = [
        (STATUS_NOT_SELECTED, 'Not Selected (Will be returned)'),
        (STATUS_SELECTED, 'Selected by User'),
        (STATUS_APPROVED, 'Approved by Admin'),
        (STATUS_REJECTED, 'Rejected by Admin'),
        (STATUS_TRANSFERRED, 'Successfully Transferred'),
        (STATUS_UNASSIGNED, 'Successfully Unassigned'),
    ]
    
    # Relationships
    transfer_request = models.ForeignKey(
        UserBranchTransferRequest,
        on_delete=models.CASCADE,
        related_name='asset_selections',
        help_text='Parent transfer request'
    )
    
    asset = models.ForeignKey(
        'assets.Asset',
        on_delete=models.CASCADE,
        related_name='transfer_selections',
        help_text='Asset being considered for transfer'
    )
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='asset_transfer_selections',
        help_text='Company context for multi-tenancy'
    )
    
    # User selection
    selected_by_user = models.BooleanField(
        default=False,
        help_text='Whether user selected this asset to transfer'
    )
    
    user_selection_reason = models.TextField(
        blank=True,
        help_text='User\'s reason for selecting this asset'
    )
    
    user_selected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When user selected/deselected this asset'
    )
    
    # Admin approval
    approved_by_admin = models.BooleanField(
        default=False,
        help_text='Whether admin approved this asset for transfer'
    )
    
    admin_decision_reason = models.TextField(
        blank=True,
        help_text='Admin\'s reason for approval/rejection'
    )
    
    admin_decision_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When admin made approval decision'
    )
    
    # Final status
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_NOT_SELECTED,
        db_index=True,
        help_text='Current status of this selection'
    )
    
    # Execution tracking
    executed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When transfer/unassignment was executed'
    )
    
    execution_error = models.TextField(
        blank=True,
        help_text='Error message if execution failed'
    )
    
    # Asset snapshot (for audit trail)
    asset_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text='Snapshot of asset state at selection time'
    )
    
    class Meta:
        db_table = 'asset_transfer_selections'
        verbose_name = 'Asset Transfer Selection'
        verbose_name_plural = 'Asset Transfer Selections'
        ordering = ['asset__category__name', 'asset__id']
        
        unique_together = [('transfer_request', 'asset')]
        
        indexes = [
            Index(fields=['transfer_request', 'status']),
            Index(fields=['transfer_request', 'selected_by_user']),
            Index(fields=['asset']),
            Index(fields=['company', 'status']),
        ]
    
    def __str__(self):
        asset_identifier = self.asset.serial_number or self.asset.asset_tag or f"Asset #{self.asset.id}"
        return f"{self.asset.category.name} {asset_identifier} - {self.get_status_display()}"
    
    def clean(self):
        """Validate model constraints"""
        super().clean()
        
        # Validate company consistency
        if self.asset.company_id != self.company_id:
            raise ValidationError("Asset must belong to the same company")
        
        if self.transfer_request.company_id != self.company_id:
            raise ValidationError("Transfer request must belong to the same company")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def create_snapshot(self):
        """Create snapshot of current asset state for audit trail"""
        # Build asset identifier
        asset_identifier = self.asset.serial_number or self.asset.asset_tag or f"Asset #{self.asset.id}"
        
        self.asset_snapshot = {
            'asset_id': self.asset.id,
            'asset_identifier': asset_identifier,
            'category': self.asset.category.name,
            'serial_number': getattr(self.asset, 'serial_number', None),
            'asset_tag': getattr(self.asset, 'asset_tag', None),
            'current_branch': self.asset.branch.name if self.asset.branch else None,
            'current_branch_id': self.asset.branch_id,
            'assigned_to': self.asset.assigned_to.username if self.asset.assigned_to else None,
            'assigned_to_id': self.asset.assigned_to_id,
            'status': self.asset.status,
            'estimated_value': str(getattr(self.asset, 'purchase_price', 0)),
            'snapshot_timestamp': timezone.now().isoformat(),
        }
        return self.asset_snapshot
