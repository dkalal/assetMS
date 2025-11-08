from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
import uuid


class AssetCategoryQuerySet(models.QuerySet):
    """Custom queryset enforcing tenant-aware filtering for categories."""

    def for_company(self, company):
        if company is None:
            return self.none()
        return self.filter(company=company)


class AssetCategoryFieldQuerySet(models.QuerySet):
    """Tenant-aware queryset for category fields."""

    def for_company(self, company):
        if company is None:
            return self.none()
        return self.filter(company=company)


class AssetQuerySet(models.QuerySet):
    def for_company(self, company):
        if company is None:
            return self.none()
        return self.filter(company=company)

    def for_branch(self, branch):
        if branch is None:
            return self
        return self.filter(branch=branch)


# Create your models here.

class AssetCategoryField(models.Model):
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
    ]
    company = models.ForeignKey(
        'tenancy.Company',
        on_delete=models.CASCADE,
        related_name='asset_category_fields',
    )
    category = models.ForeignKey('AssetCategory', on_delete=models.CASCADE, related_name='fields')
    key = models.CharField(max_length=50, help_text='Field key (e.g., serial_number)')
    label = models.CharField(max_length=100, help_text='Field label (e.g., Serial Number)')
    type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    required = models.BooleanField()

    objects = AssetCategoryFieldQuerySet.as_manager()

    class Meta:
        unique_together = ('category', 'key')
        verbose_name = 'Dynamic Field'
        verbose_name_plural = 'Dynamic Fields'
        indexes = [
            models.Index(fields=['company', 'category'], name='asset_cat_field_company_cat'),
        ]

    def clean(self):
        super().clean()
        if self.company_id is None:
            raise ValidationError('Asset category fields must belong to a company.')
        if self.category_id and self.category.company_id != self.company_id:
            raise ValidationError('Asset category field company mismatch with category company.')

    def save(self, *args, **kwargs):
        if self.category_id and not self.company_id:
            self.company_id = self.category.company_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.label} ({self.key})"


class AssetCategory(models.Model):
    company = models.ForeignKey(
        'tenancy.Company',
        on_delete=models.CASCADE,
        related_name='asset_categories',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='', help_text="Category description for better organization")
    dynamic_fields = models.JSONField(blank=True, default=dict, help_text="JSON schema for dynamic fields (auto-managed)")

    objects = AssetCategoryQuerySet.as_manager()

    class Meta:
        unique_together = ('company', 'name')
        indexes = [
            models.Index(fields=['company', 'name'], name='asset_category_company_name'),
        ]

    def clean(self):
        super().clean()
        if self.company_id is None:
            raise ValidationError('Asset categories must belong to a company.')

    def __str__(self):
        return f"{self.name} ({self.company})"

class Asset(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_IN_MAINTENANCE = 'in_maintenance'
    STATUS_RETIRED = 'retired'
    STATUS_LOST = 'lost'
    STATUS_DELETED = 'deleted'
    STATUS_TRANSFERRED = 'transferred'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_IN_MAINTENANCE, 'In Maintenance'),
        (STATUS_RETIRED, 'Retired'),
        (STATUS_LOST, 'Lost'),
        (STATUS_DELETED, 'Deleted'),
        (STATUS_TRANSFERRED, 'Transferred'),
    ]
    company = models.ForeignKey('tenancy.Company', on_delete=models.CASCADE, related_name='assets')
    branch = models.ForeignKey('tenancy.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE, related_name='assets')
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    dynamic_data = models.JSONField(default=dict, blank=True, help_text="Values for dynamic fields")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    images = models.ImageField(upload_to='asset_images/', blank=True, null=True)
    documents = models.FileField(upload_to='asset_docs/', blank=True, null=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Depreciation fields
    purchase_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Initial purchase value for depreciation")
    purchase_date = models.DateField(null=True, blank=True, help_text="Date of purchase/acquisition")
    DEPRECIATION_METHOD_CHOICES = [
        ('straight_line', 'Straight Line'),
        # Add more methods as needed
    ]
    depreciation_method = models.CharField(max_length=32, choices=DEPRECIATION_METHOD_CHOICES, default='straight_line', help_text="Depreciation method")
    useful_life_years = models.PositiveIntegerField(null=True, blank=True, help_text="Useful life in years for depreciation")
    maintenance_enabled = models.BooleanField(default=False, help_text="Enable maintenance tracking for this asset")
    maintenance_interval_days = models.PositiveIntegerField(null=True, blank=True, help_text="Maintenance interval in days (e.g., 90 for quarterly)")
    last_maintenance_date = models.DateField(null=True, blank=True, help_text="Date of last completed maintenance")
    next_maintenance_date = models.DateField(null=True, blank=True, help_text="Scheduled date for next maintenance")
    maintenance_notes = models.TextField(blank=True, help_text="General maintenance notes and requirements")
    
    # Status change tracking (world-class audit trail)
    status_changed_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of last status change")
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_status_changes',
        help_text="User who last changed the status"
    )
    status_change_reason = models.TextField(blank=True, help_text="Reason for status change")
    
    # Retirement tracking (ISO 55001 compliance)
    retired_at = models.DateField(null=True, blank=True, help_text="Date when asset was retired")
    retired_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='retired_assets',
        help_text="User who retired the asset"
    )
    retirement_reason = models.TextField(blank=True, help_text="Reason for retirement")
    disposal_method = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('sell', 'Sell'),
            ('donate', 'Donate'),
            ('scrap', 'Scrap'),
            ('recycle', 'Recycle'),
            ('transfer', 'Transfer to another entity'),
        ],
        help_text="Method of disposal"
    )
    salvage_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated salvage/resale value"
    )
    
    # Loss tracking (security & insurance compliance)
    lost_at = models.DateField(null=True, blank=True, help_text="Date when asset was reported lost/stolen")
    lost_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_lost_assets',
        help_text="User who reported the loss"
    )
    loss_reason = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('lost', 'Lost/Misplaced'),
            ('stolen', 'Stolen'),
            ('damaged_beyond_repair', 'Damaged Beyond Repair'),
        ],
        help_text="Reason for loss"
    )
    loss_details = models.TextField(blank=True, help_text="Detailed description of loss circumstances")
    police_report_number = models.CharField(max_length=100, blank=True, help_text="Police report number (if stolen)")
    last_known_location = models.CharField(max_length=255, blank=True, help_text="Last known location of asset")
    
    # Recovery tracking (asset found after being lost)
    recovered_at = models.DateField(null=True, blank=True, help_text="Date when lost asset was recovered")
    recovered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovered_assets',
        help_text="User who recovered the asset"
    )
    recovery_condition = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
            ('damaged', 'Damaged'),
        ],
        help_text="Condition of asset when recovered"
    )
    recovery_notes = models.TextField(blank=True, help_text="Notes about asset recovery")
    
    # Reactivation tracking (bringing retired asset back to service)
    reactivated_at = models.DateField(null=True, blank=True, help_text="Date when retired asset was reactivated")
    reactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reactivated_assets',
        help_text="User who reactivated the asset"
    )
    reactivation_reason = models.TextField(blank=True, help_text="Reason for reactivation")
    
    # Soft deletion tracking (30-day recovery window)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when asset was soft-deleted")
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_assets',
        help_text="User who deleted the asset"
    )
    deletion_reason = models.TextField(blank=True, help_text="Reason for deletion")
    permanent_deletion_date = models.DateField(null=True, blank=True, help_text="Date for permanent deletion (30 days after soft delete)")

    objects = AssetQuerySet.as_manager()

    def clean(self):
        super().clean()
        if self.branch and self.branch.company_id != self.company_id:
            raise ValidationError('Asset branch must belong to the same company.')
        if self.maintenance_enabled:
            if not self.maintenance_interval_days or self.maintenance_interval_days <= 0:
                raise ValidationError('Maintenance interval must be a positive integer when maintenance tracking is enabled.')
            if self.last_maintenance_date and self.next_maintenance_date and self.last_maintenance_date > self.next_maintenance_date:
                raise ValidationError('Last maintenance date cannot be after the next maintenance date.')
    
    def save(self, *args, **kwargs):
        """
        WORLD-CLASS FIX: Normalize status to lowercase before saving.
        
        This prevents the critical bug where status values are saved as capitalized
        (e.g., "Active", "In Maintenance") instead of lowercase (e.g., "active", "in_maintenance").
        
        The issue occurs when:
        1. Forms submit display values instead of database values
        2. Direct model saves without validation
        3. Data imports or migrations
        
        This defensive programming ensures data integrity at the model level,
        following ServiceNow ITAM, IBM Maximo, and SAP EAM best practices.
        """
        # Status mapping: Display value → Database value
        status_mapping = {
            'Active': self.STATUS_ACTIVE,
            'In Maintenance': self.STATUS_IN_MAINTENANCE,
            'Retired': self.STATUS_RETIRED,
            'Lost': self.STATUS_LOST,
            'Deleted': self.STATUS_DELETED,
            'Transferred': self.STATUS_TRANSFERRED,
        }
        
        # Normalize status if it's a display value
        if self.status in status_mapping:
            self.status = status_mapping[self.status]
        
        # Also handle lowercase normalization (defensive)
        if self.status:
            self.status = self.status.lower().replace(' ', '_')
        
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        return self.status != self.STATUS_DELETED

    def __str__(self):
        return f"{self.category.name} Asset #{self.pk}"


class AssetTransfer(models.Model):
    class TransferState(models.TextChoices):
        PENDING_RECEIVER = 'pending_receiver', 'Pending receiver approval'
        RECEIVER_APPROVED = 'receiver_approved', 'Receiver approved'
        RECEIVER_REJECTED = 'receiver_rejected', 'Receiver rejected'
        AWAITING_ADMIN = 'awaiting_admin', 'Awaiting admin review'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Decision(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    ACTIVE_STATES = (
        TransferState.PENDING_RECEIVER,
        TransferState.RECEIVER_APPROVED,
        TransferState.AWAITING_ADMIN,
    )

    company = models.ForeignKey('tenancy.Company', on_delete=models.CASCADE, related_name='asset_transfers')
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE, related_name='transfers')
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='initiated_asset_transfers',
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='outgoing_asset_transfers',
        null=True,
        blank=True,
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='incoming_asset_transfers',
    )
    from_branch = models.ForeignKey(
        'tenancy.Branch',
        on_delete=models.SET_NULL,
        related_name='originating_asset_transfers',
        null=True,
        blank=True,
    )
    to_branch = models.ForeignKey(
        'tenancy.Branch',
        on_delete=models.SET_NULL,
        related_name='receiving_asset_transfers',
        null=True,
        blank=True,
    )
    state = models.CharField(max_length=32, choices=TransferState.choices, default=TransferState.PENDING_RECEIVER)
    receiver_decision = models.CharField(max_length=16, choices=Decision.choices, null=True, blank=True)
    receiver_comment = models.TextField(blank=True)
    receiver_decided_at = models.DateTimeField(null=True, blank=True)
    admin_decision = models.CharField(max_length=16, choices=Decision.choices, null=True, blank=True)
    admin_comment = models.TextField(blank=True)
    admin_decided_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='approved_asset_transfers',
        null=True,
        blank=True,
        help_text="Administrator who approved the transfer when completed.",
    )
    reason = models.TextField(
        blank=True,
        default="",
        help_text="Business justification provided when the transfer was initiated.",
    )
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'state'], name='asset_tr_company_state'),
            models.Index(fields=['to_user', 'state'], name='asset_tr_to_user_state'),
            models.Index(fields=['asset', 'state'], name='asset_tr_asset_state'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['asset'],
                condition=Q(state__in=[
                    'pending_receiver',
                    'receiver_approved',
                    'awaiting_admin',
                ]),
                name='unique_active_transfer_per_asset',
            ),
        ]

    def clean(self):
        super().clean()
        if self.asset and self.company and self.asset.company_id != self.company_id:
            raise ValidationError('Transfer company must match asset company.')
        if self.from_branch and self.from_branch.company_id != self.company_id:
            raise ValidationError('Origin branch must belong to the same company.')
        if self.to_branch and self.to_branch.company_id != self.company_id:
            raise ValidationError('Destination branch must belong to the same company.')

    def save(self, *args, **kwargs):
        if self.asset_id and not self.company_id:
            self.company = self.asset.company
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        return self.state in self.ACTIVE_STATES

    def __str__(self):
        return f"Transfer #{self.pk} for asset {self.asset_id} ({self.get_state_display()})"


class MaintenanceRecord(models.Model):
    """Track scheduled and completed maintenance executions for assets."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE, related_name='maintenance_records')
    company = models.ForeignKey('tenancy.Company', on_delete=models.CASCADE, related_name='maintenance_records')
    branch = models.ForeignKey('tenancy.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_records')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    scheduled_for = models.DateField(help_text="Planned maintenance date.")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='performed_maintenance_records',
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='supervised_maintenance_records',
    )
    description = models.TextField(blank=True)
    outcome_notes = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_maintenance_records',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='updated_maintenance_records',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_for', '-created_at']
        indexes = [
            models.Index(fields=['company', 'scheduled_for'], name='maint_company_sched_idx'),
            models.Index(fields=['company', 'status'], name='maint_company_status_idx'),
            models.Index(fields=['asset', 'status'], name='maint_asset_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(cost__gte=0), name='maintenance_cost_non_negative'),
        ]

    def clean(self):
        super().clean()
        if self.asset and self.company and self.asset.company_id != self.company_id:
            raise ValidationError('Maintenance record company must match asset company.')
        if self.branch and self.branch.company_id != self.company_id:
            raise ValidationError('Maintenance record branch must belong to the same company.')
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            raise ValidationError('Maintenance completion time cannot precede the start time.')

    def save(self, *args, **kwargs):
        if self.asset_id:
            if not self.company_id:
                self.company = self.asset.company
            if not self.branch_id:
                self.branch = self.asset.branch
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Maintenance {self.get_status_display()} for asset {self.asset_id} on {self.scheduled_for}"


class ExportLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    format = models.CharField(max_length=10)
    columns = models.JSONField()
    filters = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Export by {self.user} on {self.timestamp:%Y-%m-%d %H:%M} ({self.format})"
