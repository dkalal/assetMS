"""
Account Management Models
=========================
Purpose: User registration, invitations, onboarding, and company subscriptions
Inspired by: Slack, Salesforce, ServiceNow, Asana

Models:
- UserInvitation: Email invitation system
- CompanyRegistration: SaaS subscription tracking
- OnboardingProgress: Wizard completion tracking
"""

import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class UserInvitation(models.Model):
    """
    User invitation system - Slack/GitHub pattern
    
    Allows admins to invite users via email with role and branch assignment.
    Invitations expire after 7 days and are single-use.
    
    Security:
    - Cryptographically secure tokens
    - Company-scoped (admin can only invite to their company)
    - Expiry enforcement
    - Status tracking
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'tenancy.Company',
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text="Company the user is invited to join"
    )
    email = models.EmailField(help_text="Email address of invitee")
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=20,
        choices=settings.AUTH_USER_MODEL and [(r, r.title()) for r in ['admin', 'manager', 'user']],
        help_text="Role to assign upon acceptance"
    )
    branch = models.ForeignKey(
        'tenancy.Branch',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invitations',
        help_text="Branch to assign user to"
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations',
        help_text="Admin who sent the invitation"
    )
    invitation_token = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Secure token for invitation link"
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        help_text="Invitation expires 7 days after sending"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    class Meta:
        db_table = 'user_invitations'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['company', 'status'], name='invitation_company_status_idx'),
            models.Index(fields=['email', 'status'], name='invitation_email_status_idx'),
        ]
        verbose_name = 'User Invitation'
        verbose_name_plural = 'User Invitations'
    
    def __str__(self):
        return f"{self.email} → {self.company.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Set expiry date if not set (7 days from now)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        
        # Generate secure token if not set
        if not self.invitation_token:
            import secrets
            self.invitation_token = secrets.token_urlsafe(32)
        
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if invitation is still valid"""
        return (
            self.status == 'pending' and
            timezone.now() < self.expires_at
        )
    
    def mark_expired(self):
        """Mark invitation as expired"""
        if self.status == 'pending' and timezone.now() >= self.expires_at:
            self.status = 'expired'
            self.save(update_fields=['status'])
            return True
        return False
    
    def accept(self, user):
        """Mark invitation as accepted"""
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save(update_fields=['status', 'accepted_at'])
    
    def cancel(self):
        """Cancel pending invitation"""
        if self.status == 'pending':
            self.status = 'cancelled'
            self.save(update_fields=['status'])
            return True
        return False
    
    def clean(self):
        super().clean()
        
        # Validate branch belongs to company
        if self.branch and self.branch.company != self.company:
            raise ValidationError({
                'branch': 'Branch must belong to the same company'
            })
        
        # Check if email already registered in this company
        from users.models import User
        if User.objects.filter(email=self.email, company=self.company).exists():
            raise ValidationError({
                'email': f'User with this email already exists in {self.company.name}'
            })


class CompanyRegistration(models.Model):
    """
    SaaS company registration - Salesforce pattern
    
    Tracks self-service signups and subscription status.
    Links to Company model for complete profile.
    
    Features:
    - Plan selection (free, pro, enterprise)
    - Trial management (14 days)
    - Subscription status tracking
    - Stripe integration ready
    """
    
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    SUBSCRIPTION_STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ]
    
    company = models.OneToOneField(
        'tenancy.Company',
        on_delete=models.CASCADE,
        related_name='registration',
        help_text="Company profile"
    )
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='free',
        help_text="Subscription plan"
    )
    trial_ends_at = models.DateField(
        null=True,
        blank=True,
        help_text="Trial period end date (14 days from signup)"
    )
    billing_email = models.EmailField(help_text="Email for billing communications")
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default='trial',
        db_index=True
    )
    
    # Payment integration (reserved for future use)
    # Will be implemented when payment method is selected
    payment_provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="Payment provider (e.g., 'stripe', 'paypal', 'mpesa') - to be configured"
    )
    payment_customer_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Customer ID in payment provider system"
    )
    payment_subscription_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Subscription ID in payment provider system"
    )
    
    # Resource limits
    max_users = models.IntegerField(
        default=5,
        help_text="Maximum number of users allowed"
    )
    max_assets = models.IntegerField(
        default=100,
        help_text="Maximum number of assets allowed"
    )
    max_storage_mb = models.IntegerField(
        default=1000,
        help_text="Maximum storage in MB"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'company_registrations'
        verbose_name = 'Company Registration'
        verbose_name_plural = 'Company Registrations'
    
    def __str__(self):
        return f"{self.company.name} - {self.get_plan_display()} ({self.get_subscription_status_display()})"
    
    def save(self, *args, **kwargs):
        # Set trial end date if not set (14 days from now)
        if not self.trial_ends_at and self.subscription_status == 'trial':
            self.trial_ends_at = (timezone.now() + timedelta(days=14)).date()
        
        # Set resource limits based on plan
        if self.plan == 'free':
            self.max_users = 5
            self.max_assets = 100
            self.max_storage_mb = 1000
        elif self.plan == 'pro':
            self.max_users = 50
            self.max_assets = 10000
            self.max_storage_mb = 10000
        elif self.plan == 'enterprise':
            self.max_users = -1  # Unlimited
            self.max_assets = -1  # Unlimited
            self.max_storage_mb = -1  # Unlimited
        
        super().save(*args, **kwargs)
    
    def is_trial_expired(self):
        """Check if trial period has ended"""
        if self.subscription_status == 'trial' and self.trial_ends_at:
            return timezone.now().date() > self.trial_ends_at
        return False
    
    def days_until_trial_ends(self):
        """Get number of days remaining in trial"""
        if self.subscription_status == 'trial' and self.trial_ends_at:
            delta = self.trial_ends_at - timezone.now().date()
            return delta.days
        return None
    
    def can_add_user(self):
        """Check if company can add more users"""
        if self.max_users == -1:  # Unlimited
            return True
        
        from users.models import User
        current_count = User.objects.filter(company=self.company).count()
        return current_count < self.max_users
    
    def can_add_asset(self):
        """Check if company can add more assets"""
        if self.max_assets == -1:  # Unlimited
            return True
        
        from assets.models import Asset
        current_count = Asset.objects.filter(company=self.company).count()
        return current_count < self.max_assets
    
    def get_trial_status_message(self):
        """Get user-friendly trial status message"""
        if self.subscription_status != 'trial':
            return None
        
        days_left = self.days_until_trial_ends()
        if days_left is None:
            return None
        
        if days_left > 7:
            return f"Your free trial has {days_left} days remaining"
        elif days_left > 0:
            return f"⚠️ Your trial expires in {days_left} days"
        else:
            return "❌ Your trial has expired. Please contact support to continue."
    
    def suspend_if_trial_expired(self):
        """Auto-suspend company if trial expired (called by scheduled task)"""
        if self.is_trial_expired() and self.subscription_status == 'trial':
            self.subscription_status = 'suspended'
            self.save(update_fields=['subscription_status'])
            
            # Deactivate all users in company (soft delete)
            from users.models import User
            User.objects.filter(company=self.company, is_active=True).update(is_active=False)
            
            return True
        return False


class OnboardingProgress(models.Model):
    """
    Onboarding wizard progress - Asana pattern
    
    Tracks user's completion of onboarding steps.
    Helps guide new users through initial setup.
    
    Steps:
    1. Company details (industry, size, timezone)
    2. Invite team (optional)
    3. Quick tour (feature overview)
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='onboarding',
        help_text="User completing onboarding"
    )
    
    # Step completion flags
    company_details_completed = models.BooleanField(
        default=False,
        help_text="Step 1: Company profile filled"
    )
    team_invited = models.BooleanField(
        default=False,
        help_text="Step 2: Team members invited"
    )
    tour_completed = models.BooleanField(
        default=False,
        help_text="Step 3: Product tour completed"
    )
    first_asset_created = models.BooleanField(
        default=False,
        help_text="Bonus: First asset registered"
    )
    
    # Progress tracking
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When onboarding was fully completed"
    )
    current_step = models.IntegerField(
        default=1,
        help_text="Current step number (1-3)"
    )
    skipped = models.BooleanField(
        default=False,
        help_text="User clicked 'Skip Onboarding'"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'onboarding_progress'
        verbose_name = 'Onboarding Progress'
        verbose_name_plural = 'Onboarding Progress Records'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.completion_percentage}% complete"
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage"""
        steps = [
            self.company_details_completed,
            self.team_invited,
            self.tour_completed,
        ]
        completed = sum(1 for step in steps if step)
        return int((completed / len(steps)) * 100)
    
    def mark_completed(self):
        """Mark onboarding as fully completed"""
        if not self.completed_at:
            self.completed_at = timezone.now()
            self.current_step = 4  # Beyond last step
            self.save(update_fields=['completed_at', 'current_step'])
            
            # Update user model
            self.user.onboarding_completed = True
            self.user.save(update_fields=['onboarding_completed'])
    
    def advance_to_next_step(self):
        """Move to next onboarding step"""
        if self.current_step < 3:
            self.current_step += 1
            self.save(update_fields=['current_step'])
    
    def skip_onboarding(self):
        """User chose to skip onboarding"""
        self.skipped = True
        self.completed_at = timezone.now()
        self.save(update_fields=['skipped', 'completed_at'])
        
        # Still mark user as onboarded
        self.user.onboarding_completed = True
        self.user.save(update_fields=['onboarding_completed'])
