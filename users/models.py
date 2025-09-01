from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid

class User(AbstractUser):
    ADMIN = 'admin'
    MANAGER = 'manager'
    USER = 'user'
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (MANAGER, 'Manager'),
        (USER, 'User'),
    ]
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

    def __str__(self):
        return f"{self.username} ({self.role})"

    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(str(self.role), self.role)
    
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
