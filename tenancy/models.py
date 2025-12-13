from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


class CompanyScopedQuerySet(models.QuerySet):
    def for_company(self, company):
        if company is None:
            return self.none()
        return self.filter(company=company)

    def for_branch(self, branch):
        if branch is None:
            return self
        return self.filter(branch=branch)


class CompanyScopedManager(models.Manager.from_queryset(CompanyScopedQuerySet)):  # type: ignore[misc]
    def get_queryset(self):
        return super().get_queryset().select_related("company")


class CompanyScopedModel(models.Model):
    """Abstract base ensuring all queries respect company scoping."""

    company = models.ForeignKey(
        "tenancy.Company",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_items",
    )

    objects = CompanyScopedManager()

    class Meta:
        abstract = True


class BranchQuerySet(CompanyScopedQuerySet):
    def active(self):
        return self.filter(is_active=True)


class BranchScopedQuerySet(CompanyScopedQuerySet):
    def for_branch(self, branch):
        if branch is None:
            return self
        return self.filter(branch=branch)


class BranchScopedManager(models.Manager.from_queryset(BranchScopedQuerySet)):  # type: ignore[misc]
    def get_queryset(self):
        return super().get_queryset().select_related("company", "branch")


class BranchScopedModel(CompanyScopedModel):
    """Abstract base guaranteeing presence of branch foreign key."""

    branch = models.ForeignKey(
        "tenancy.Branch",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_items",
        null=True,
        blank=True,
    )

    objects = BranchScopedManager()

    class Meta:
        abstract = True


class Company(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to="company/logos/", null=True, blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Companies"

    def __str__(self) -> str:
        return self.name


class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    code = models.CharField(max_length=50)
    is_head_office = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Branch Manager Assignment
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_branches',
        help_text="Primary manager responsible for this branch",
        limit_choices_to={'is_active': True}
    )
    manager_assigned_at = models.DateTimeField(null=True, blank=True)
    manager_assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branch_manager_assignments_made',
        help_text="Admin who assigned the current manager"
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BranchQuerySet.as_manager()

    class Meta:
        ordering = ["company__name", "name"]
        unique_together = ("company", "code")
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                condition=Q(is_head_office=True),
                name="unique_head_office_per_company",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "is_active"], name="branch_company_active_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        if self.is_head_office:
            existing = Branch.objects.filter(company=self.company, is_head_office=True)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError("Company already has a head office branch.")
        if not self.is_active:
            if self.is_head_office:
                raise ValidationError("Head office branch cannot be deactivated.")
            other_active = Branch.objects.filter(company=self.company, is_active=True)
            if self.pk:
                other_active = other_active.exclude(pk=self.pk)
            if not other_active.exists():
                raise ValidationError("Company must retain at least one active branch.")
        
        # Validate manager belongs to the same company
        if self.manager:
            if not hasattr(self.manager, 'company') or self.manager.company != self.company:
                raise ValidationError(
                    f"Manager {self.manager.username} must belong to the same company as the branch."
                )
            # Validate manager has appropriate role
            if hasattr(self.manager, 'role'):
                valid_roles = ['admin', 'manager']
                if self.manager.role not in valid_roles:
                    raise ValidationError(
                        f"User {self.manager.username} must have 'manager' or 'admin' role to manage a branch."
                    )

    def __str__(self) -> str:
        return f"{self.name} ({self.company})"


class UserBranch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_branches")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="user_branches")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="memberships")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "branch")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company"],
                condition=Q(is_primary=True),
                name="unique_primary_branch_per_user_company",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.branch.company_id != self.company_id:
            raise ValidationError("Branch company mismatch for membership.")

    def save(self, *args, **kwargs):
        if self.branch_id and not self.company_id:
            self.company = self.branch.company
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        label = f"{self.user} → {self.branch}"
        if self.is_primary:
            label += " [primary]"
        return label

    @classmethod
    def ensure_primary(cls, user, company, branch):
        """Atomically set the provided branch as the user's primary branch."""
        with transaction.atomic():
            cls.objects.filter(user=user, company=company, is_primary=True).exclude(branch=branch).update(is_primary=False, updated_at=timezone.now())
            membership, _ = cls.objects.get_or_create(
                user=user,
                company=company,
                branch=branch,
                defaults={"is_primary": True},
            )
            if not membership.is_primary:
                membership.is_primary = True
                membership.save(update_fields=["is_primary", "updated_at"])
            return membership


class Alert(models.Model):
    LEVEL_INFO = "info"
    LEVEL_SUCCESS = "success"
    LEVEL_WARNING = "warning"
    LEVEL_ERROR = "error"
    LEVEL_CHOICES = [
        (LEVEL_INFO, "Info"),
        (LEVEL_SUCCESS, "Success"),
        (LEVEL_WARNING, "Warning"),
        (LEVEL_ERROR, "Error"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="alerts")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="alerts", null=True, blank=True)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    message = models.TextField()
    context = models.JSONField(blank=True, default=dict)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["company", "branch", "created_at"]),
        ]

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def mark_unread(self):
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=["is_read", "read_at"])

    def __str__(self) -> str:
        scope = self.branch or self.company
        return f"[{self.level.upper()}] {self.recipient} @ {scope}: {self.message[:40]}"


# Import approval models
from tenancy.approval_models import ApprovalRequest  # noqa: E402

# Import policy models
from tenancy.policy_models import MultiTenancyPolicy  # noqa: E402
