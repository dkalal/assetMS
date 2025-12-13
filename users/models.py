from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
import uuid

class User(AbstractUser):
    ADMIN = 'admin'
    MANAGER = 'manager'
    USER = 'user'
    ROLE_CHOICES = [
        (ADMIN, 'Administrator'),
        (MANAGER, 'Manager'),
        (USER, 'User'),
    ]
    company = models.ForeignKey('tenancy.Company', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=USER)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True, help_text='User avatar/profile image')
    phone_number = models.CharField(max_length=32, blank=True, null=True, help_text='Contact phone number')
    
    # Enterprise IAM fields
    is_invited = models.BooleanField(default=False)
    invitation_token = models.CharField(max_length=100, blank=True, null=True)
    invitation_sent_at = models.DateTimeField(blank=True, null=True)
    last_activity = models.DateTimeField(auto_now=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(blank=True, null=True)
    force_password_change = models.BooleanField(default=False)
    session_timeout_minutes = models.IntegerField(default=60)
    
    # Email verification (SaaS onboarding)
    email_verified = models.BooleanField(default=False, help_text="Email address verified")
    email_verification_token = models.CharField(max_length=100, blank=True, db_index=True, help_text="Secure token for email verification")
    email_verification_sent_at = models.DateTimeField(null=True, blank=True, help_text="When verification email was sent")
    
    # System roles (multi-tenant SaaS)
    is_system_admin = models.BooleanField(default=False, help_text="Super admin (not tied to company)")
    onboarding_completed = models.BooleanField(default=False, help_text="User completed onboarding wizard")
    
    # WORLD-CLASS: User Retirement Fields (ServiceNow ITAM, IBM Maximo, SAP EAM pattern)
    retired_at = models.DateTimeField(null=True, blank=True, help_text="When user was retired/deactivated")
    retired_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='retired_users', help_text="Admin who retired this user")

    def __str__(self):
        company = getattr(self, 'company', None)
        company_label = f" @ {company.name}" if company else ''
        return f"{self.username} ({self.role}){company_label}"

    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(str(self.role), self.role)
    
    def get_display_name(self):
        """Return name with (Inactive) suffix if retired - ServiceNow ITAM pattern"""
        name = self.get_full_name() or self.username
        if not self.is_active:
            return f"{name} (Inactive)"
        return name
    
    @property
    def is_account_locked(self):
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def generate_invitation_token(self):
        self.invitation_token = str(uuid.uuid4())
        self.invitation_sent_at = timezone.now()
        self.is_invited = True
        self.save()
        return self.invitation_token

    @cached_property
    def primary_branch_membership(self):
        if not self.company_id:
            return None
        return self.user_branches.select_related('branch').filter(company_id=self.company_id, is_primary=True).first()

    @property
    def primary_branch(self):
        membership = self.primary_branch_membership
        return membership.branch if membership else None

    class Meta:
        permissions = [
            ("can_manage_users", "Can manage users and their permissions"),
            ("can_manage_assets", "Can manage assets"),
            ("can_manage_categories", "Can manage asset categories"),
            ("can_manage_reports", "Can generate and manage reports"),
            ("can_view_audit_logs", "Can view audit logs"),
        ]

class RolePermissionMatrix(models.Model):
    """Singleton model storing role-to-permissions matrix.
    Keeps enterprise defaults and allows admin customization.
    """
    SINGLETON_KEY = 'roles_permissions_singleton'

    singleton = models.CharField(max_length=64, unique=True, default=SINGLETON_KEY, editable=False)
    permissions = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'role_permission_matrix'

    def __str__(self):
        return 'Role Permission Matrix'

    @staticmethod
    def default_matrix():
        # Match current frontend behavior
        return {
            'Admin': [
                'view_assets', 'create_assets', 'edit_assets', 'delete_assets',
                'manage_users', 'view_reports', 'export_data', 'system_admin'
            ],
            'Manager': [
                'view_assets', 'create_assets', 'edit_assets', 'view_reports', 'export_data'
            ],
            'User': [
                'view_assets'
            ],
        }

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(
            singleton=cls.SINGLETON_KEY,
            defaults={'permissions': cls.default_matrix()},
        )
        # Ensure it always has at least defaults
        if not obj.permissions:
            obj.permissions = cls.default_matrix()
            obj.save(update_fields=['permissions'])
        return obj

class UserSession(models.Model):
    """Enterprise concurrent multi-session tracking"""
    SESSION_CONTEXT_CHOICES = [
        ('web', 'Web Application'),
        ('admin', 'Django Admin'),
        ('api', 'API Access'),
        ('mobile', 'Mobile App'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, db_index=True)
    session_context = models.CharField(max_length=20, choices=SESSION_CONTEXT_CHOICES, default='web')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    browser_fingerprint = models.CharField(max_length=100, db_index=True)
    tab_id = models.CharField(max_length=36, blank=True)  # UUID for tab identification
    device_fingerprint = models.CharField(max_length=100, blank=True)  # Device-level fingerprint
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    logout_reason = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'user_sessions'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key', 'is_active']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.session_context} ({self.browser_fingerprint[:8]})"
    
    @property
    def is_expired(self):
        """Check if session is expired based on user timeout settings"""
        if not self.is_active:
            return True
        timeout_minutes = self.user.session_timeout_minutes
        expiry_time = self.last_activity + timezone.timedelta(minutes=timeout_minutes)
        return timezone.now() > expiry_time

class AccessLog(models.Model):
    """Enterprise access logging"""
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('failed_login', 'Failed Login'),
        ('password_change', 'Password Change'),
        ('account_locked', 'Account Locked'),
        ('account_activated', 'Account Activated'),
        ('account_deactivated', 'Account Deactivated'),
        ('profile_updated', 'Profile Updated'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    
    class Meta:
        db_table = 'access_logs'
        ordering = ['-timestamp']


class UserRetirement(models.Model):
    """
    WORLD-CLASS: Self-Service User Retirement Requests with Approval Workflow
    
    Inspired by:
    - ServiceNow ITSM: Employee separation requests with multi-level approvals
    - SAP SuccessFactors: Employee-initiated separation with manager approval  
    - Workday HCM: Self-service termination with workflow automation
    - Oracle HCM Cloud: Voluntary termination with asset return process
    
    Purpose:
    - Allow employees to request their own retirement/separation
    - Manager/Admin approval workflow
    - Track asset handover and access revocation
    - Maintain complete audit trail for compliance (SOX, GDPR, ISO 55001)
    
    Workflow:
    1. requested: Employee submits retirement request
    2. pending_approval: Waiting for manager/admin approval
    3. approved: Approved, waiting for effective date
    4. in_progress: Active separation process
    5. asset_handover: Assets being collected/reassigned
    6. final_review: Admin final review before completion
    7. completed: Account deactivated
    8. rejected: Request denied
    9. cancelled: Request cancelled
    """
    
    # Status Constants
    STATUS_REQUESTED = 'requested'
    STATUS_PENDING_APPROVAL = 'pending_approval'
    STATUS_APPROVED = 'approved'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_ASSET_HANDOVER = 'asset_handover'
    STATUS_FINAL_REVIEW = 'final_review'
    STATUS_COMPLETED = 'completed'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_REQUESTED, 'Requested'),
        (STATUS_PENDING_APPROVAL, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_ASSET_HANDOVER, 'Asset Handover'),
        (STATUS_FINAL_REVIEW, 'Final Review'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    # Reason Categories
    REASON_RESIGNATION = 'resignation'
    REASON_RETIREMENT = 'retirement'
    REASON_CAREER_CHANGE = 'career_change'
    REASON_RELOCATION = 'relocation'
    REASON_PERSONAL = 'personal'
    REASON_TERMINATION = 'termination'
    REASON_CONTRACT_END = 'contract_end'
    REASON_OTHER = 'other'
    
    REASON_CATEGORY_CHOICES = [
        (REASON_RESIGNATION, 'Resignation'),
        (REASON_RETIREMENT, 'Retirement'),
        (REASON_CAREER_CHANGE, 'Career Change'),
        (REASON_RELOCATION, 'Relocation'),
        (REASON_PERSONAL, 'Personal Reasons'),
        (REASON_TERMINATION, 'Termination'),
        (REASON_CONTRACT_END, 'Contract End'),
        (REASON_OTHER, 'Other'),
    ]
    
    # Core Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='retirement_requests', help_text="Employee requesting retirement")
    company = models.ForeignKey('tenancy.Company', on_delete=models.CASCADE, help_text="Company context for multi-tenancy")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_REQUESTED)
    
    # Request Details
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='submitted_retirement_requests', help_text="Person who submitted request (usually self)")
    request_date = models.DateTimeField(auto_now_add=True, help_text="When request was submitted")
    effective_date = models.DateField(help_text="Desired last working day")
    reason_category = models.CharField(max_length=50, choices=REASON_CATEGORY_CHOICES, default=REASON_RESIGNATION)
    reason = models.TextField(help_text="Detailed reason for retirement")
    notes = models.TextField(blank=True, help_text="Additional notes from employee")
    
    # Approval Workflow
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_retirements', help_text="Manager/Admin who reviewed request")
    reviewed_at = models.DateTimeField(null=True, blank=True, help_text="When request was reviewed")
    approval_notes = models.TextField(blank=True, help_text="Comments from approver")
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection if denied")
    
    # Asset Management
    asset_count = models.IntegerField(default=0, help_text="Total number of assigned assets")
    assets_returned = models.IntegerField(default=0, help_text="Number of assets returned")
    assets_pending = models.IntegerField(default=0, help_text="Number of assets pending return")
    
    # Processing
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_retirements', help_text="Admin processing retirement")
    processing_started_at = models.DateTimeField(null=True, blank=True, help_text="When processing started")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When retirement completed")
    completed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='completed_retirements', help_text="Admin who completed retirement")
    
    # Compliance Checklist
    exit_interview_completed = models.BooleanField(default=False, help_text="Exit interview conducted")
    exit_interview_notes = models.TextField(blank=True, help_text="Exit interview notes")
    access_revoked = models.BooleanField(default=False, help_text="System access revoked")
    final_paycheck_processed = models.BooleanField(default=False, help_text="Final paycheck processed")
    benefits_terminated = models.BooleanField(default=False, help_text="Benefits terminated")
    
    # Legacy Fields (for backward compatibility)
    retired_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='initiated_retirements', help_text="[DEPRECATED] Use requested_by instead")
    created_at = models.DateTimeField(auto_now_add=True, help_text="[DEPRECATED] Use request_date instead")
    
    class Meta:
        db_table = 'user_retirements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
        verbose_name = 'User Retirement'
        verbose_name_plural = 'User Retirements'
    
    def __str__(self):
        return f"Retirement Request: {self.user.get_full_name()} - {self.get_status_display()}"
    
    # Status Check Properties
    @property
    def is_requested(self):
        """Request submitted, not yet reviewed"""
        return self.status == self.STATUS_REQUESTED
    
    @property
    def is_pending_approval(self):
        """Waiting for manager/admin approval"""
        return self.status == self.STATUS_PENDING_APPROVAL
    
    @property
    def is_approved(self):
        """Approved, waiting for processing"""
        return self.status == self.STATUS_APPROVED
    
    @property
    def is_rejected(self):
        """Request denied"""
        return self.status == self.STATUS_REJECTED
    
    @property
    def is_in_progress(self):
        """Currently being processed"""
        return self.status == self.STATUS_IN_PROGRESS
    
    @property
    def is_completed(self):
        """Retirement completed"""
        return self.status == self.STATUS_COMPLETED
    
    @property
    def is_cancelled(self):
        """Request cancelled"""
        return self.status == self.STATUS_CANCELLED
    
    @property
    def can_be_approved(self):
        """Check if request can be approved"""
        return self.status in [self.STATUS_REQUESTED, self.STATUS_PENDING_APPROVAL]
    
    @property
    def can_be_cancelled(self):
        """Check if request can be cancelled"""
        return self.status not in [self.STATUS_COMPLETED, self.STATUS_REJECTED, self.STATUS_CANCELLED]
    
    @property
    def is_self_requested(self):
        """Check if user requested their own retirement"""
        return self.requested_by == self.user
    
    # Time Calculations
    @property
    def duration_days(self):
        """Calculate duration of retirement process in days"""
        if self.completed_at:
            return (self.completed_at - self.request_date).days
        return (timezone.now() - self.request_date).days
    
    @property
    def days_until_effective(self):
        """Calculate days until effective date"""
        from datetime import date
        if self.effective_date:
            delta = (self.effective_date - date.today()).days
            return delta if delta > 0 else 0
        return None
    
    @property
    def is_effective_date_reached(self):
        """Check if effective date has been reached"""
        from datetime import date
        return self.effective_date and self.effective_date <= date.today()
    
    # Asset Management
    @property
    def assets_return_progress(self):
        """Calculate asset return progress percentage"""
        if self.asset_count == 0:
            return 100
        return int((self.assets_returned / self.asset_count) * 100)
    
    @property
    def all_assets_returned(self):
        """Check if all assets have been returned"""
        return self.asset_count > 0 and self.assets_returned == self.asset_count
    
    # Compliance Checklist
    @property
    def compliance_score(self):
        """Calculate compliance checklist completion percentage"""
        checklist = [
            self.exit_interview_completed,
            self.access_revoked,
            self.final_paycheck_processed,
            self.benefits_terminated,
            self.all_assets_returned,
        ]
        completed = sum(1 for item in checklist if item)
        return int((completed / len(checklist)) * 100)
    
    @property
    def is_ready_for_completion(self):
        """Check if all requirements met for completion"""
        return (
            self.all_assets_returned and
            self.access_revoked and
            self.status == self.STATUS_FINAL_REVIEW
        )
    
    # Display Methods
    def get_approval_status_color(self):
        """Get Bootstrap color class for status badge"""
        status_colors = {
            self.STATUS_REQUESTED: 'info',
            self.STATUS_PENDING_APPROVAL: 'warning',
            self.STATUS_APPROVED: 'success',
            self.STATUS_IN_PROGRESS: 'primary',
            self.STATUS_ASSET_HANDOVER: 'primary',
            self.STATUS_FINAL_REVIEW: 'warning',
            self.STATUS_COMPLETED: 'success',
            self.STATUS_REJECTED: 'danger',
            self.STATUS_CANCELLED: 'secondary',
        }
        return status_colors.get(self.status, 'secondary')
    
    def get_timeline_events(self):
        """Get list of timeline events for display (JSON-serializable)"""
        events = []
        
        if self.request_date:
            events.append({
                'date': self.request_date.isoformat(),
                'title': 'Request Submitted',
                'description': f"By {self.requested_by.get_full_name()}",
                'icon': 'bi-file-earmark-plus',
                'color': 'info'
            })
        
        if self.reviewed_at and self.reviewed_by:
            status_text = 'Approved' if self.is_approved else 'Rejected'
            events.append({
                'date': self.reviewed_at.isoformat(),
                'title': f'Request {status_text}',
                'description': f"By {self.reviewed_by.get_full_name()}",
                'icon': 'bi-check-circle' if self.is_approved else 'bi-x-circle',
                'color': 'success' if self.is_approved else 'danger'
            })
        
        if self.processing_started_at and self.processed_by:
            events.append({
                'date': self.processing_started_at.isoformat(),
                'title': 'Processing Started',
                'description': f"By {self.processed_by.get_full_name()}",
                'icon': 'bi-gear',
                'color': 'primary'
            })
        
        if self.completed_at and self.completed_by:
            events.append({
                'date': self.completed_at.isoformat(),
                'title': 'Retirement Completed',
                'description': f"By {self.completed_by.get_full_name()}",
                'icon': 'bi-check-circle-fill',
                'color': 'success'
            })
        
        # Sort by date string (ISO format is sortable)
        return sorted(events, key=lambda x: x['date'])
