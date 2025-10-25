from __future__ import annotations

from typing import Optional

from django import forms
from django.db import IntegrityError

from .models import Branch, Company, UserBranch


class CompanyUpdateForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            "name",
            "address",
            "tax_id",
            "contact_person",
            "phone",
            "email",
            "timezone",
            "logo",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tax_id": forms.TextInput(attrs={"class": "form-control"}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "timezone": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class BranchForm(forms.ModelForm):
    set_as_primary = forms.BooleanField(
        required=False,
        initial=True,
        help_text="If selected, you will become the primary user for this branch.",
    )

    class Meta:
        model = Branch
        fields = ["name", "code", "address", "is_head_office", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "is_head_office": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.company: Optional[Company] = kwargs.pop("company", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._can_manage_status = bool(
            self.user
            and (
                getattr(self.user, "role", None) == getattr(self.user.__class__, "ADMIN", "admin")
                or getattr(self.user, "is_superuser", False)
            )
        )
        if self.company is not None:
            self.instance.company = self.company
        else:
            self.fields["name"].disabled = True
            self.fields["code"].disabled = True
            self.fields["address"].disabled = True
            self.fields["is_head_office"].disabled = True
            self.fields["set_as_primary"].disabled = True
            self.fields["is_active"].disabled = True
        if self.instance and self.instance.pk:
            active_initial = self.instance.is_active
        else:
            active_initial = True
        if self._can_manage_status:
            self.fields["is_active"].initial = active_initial
            self.fields["is_active"].help_text = "Inactive branches are hidden from dashboards and selectors but retained for audit continuity."
        else:
            # Non-admin users cannot change the active flag
            self.fields["is_active"].widget = forms.HiddenInput()
            self.fields["is_active"].initial = active_initial

        disable_primary = False
        if self.instance and self.instance.pk:
            if self.user is not None:
                is_primary = UserBranch.objects.filter(
                    user=self.user,
                    company=self.company,
                    branch=self.instance,
                ).exists()
                self.fields["set_as_primary"].initial = is_primary
            else:
                self.fields["set_as_primary"].initial = False
            if not active_initial:
                disable_primary = True

        if not self.instance or not self.instance.pk:
            disable_primary = False
            if not active_initial:
                disable_primary = True

        if not self._can_manage_status:
            disable_primary = True

        if disable_primary:
            self.fields["set_as_primary"].widget.attrs["disabled"] = True
            self.fields["set_as_primary"].widget.attrs["aria-disabled"] = "true"

    def clean(self):
        if self.company is None:
            raise forms.ValidationError("Company context is required to create a branch.")
        cleaned_data = super().clean()
        self.instance.company = self.company

        if self.instance and self.instance.pk:
            try:
                current_state = Branch.objects.only("is_active").get(pk=self.instance.pk).is_active
                self.instance.is_active = current_state
            except Branch.DoesNotExist:
                pass

        code = cleaned_data.get("code")
        if code:
            queryset = Branch.objects.filter(company=self.company, code__iexact=code)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                self.add_error("code", "Branch code must be unique per company.")

        is_active = cleaned_data.get("is_active", True)
        is_active_field_name = self.add_prefix("is_active")
        if self._can_manage_status and is_active_field_name not in self.data:
            is_active = self.instance.is_active if self.instance.pk else True
            cleaned_data["is_active"] = is_active
        if not self._can_manage_status:
            # Preserve existing state for non-admin users
            is_active = self.instance.is_active if self.instance.pk else True
            cleaned_data["is_active"] = is_active
        if not is_active and cleaned_data.get("set_as_primary"):
            self.add_error("set_as_primary", "Inactive branches cannot be set as primary.")
        self.instance.is_active = bool(is_active)

        return cleaned_data

    def save(self, user=None, commit=True):
        branch: Branch = super().save(commit=False)
        branch.company = self.company
        if commit:
            try:
                branch.save()
            except IntegrityError as exc:
                raise forms.ValidationError("Unable to save branch. Ensure the code is unique for your company.") from exc
        if (
            user is not None
            and self.cleaned_data.get("set_as_primary")
            and branch.pk
        ):
            UserBranch.ensure_primary(user=user, company=self.company, branch=branch)
        return branch


class UserBranchAssignmentForm(forms.Form):
    """
    Admin-only form for assigning primary branches to users.
    
    Enforces company scoping and validates branch activity status.
    This form allows administrators to change the primary branch for any user
    within their company while maintaining strict multi-tenant isolation.
    
    Security:
    - Company-scoped querysets prevent cross-tenant data access
    - Validates user and branch belong to the same company
    - Ensures only active branches can be set as primary
    - Uses atomic transactions for data consistency
    
    Usage:
        form = UserBranchAssignmentForm(
            request.POST,
            company=request.company,
            admin_user=request.user
        )
        if form.is_valid():
            membership = form.save()
    """
    user = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="User",
        help_text="Select the user whose primary branch you want to update."
    )
    primary_branch = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Primary Branch",
        help_text="Select the active branch to set as primary for this user."
    )

    def __init__(self, *args, **kwargs):
        self.company: Optional[Company] = kwargs.pop("company", None)
        self.admin_user = kwargs.pop("admin_user", None)
        super().__init__(*args, **kwargs)
        
        if self.company is None:
            raise ValueError("Company context is required for UserBranchAssignmentForm.")
        
        # Scope users to company - only active users
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields["user"].queryset = User.objects.filter(
            company=self.company,
            is_active=True
        ).select_related("company").order_by("username")
        
        # Scope branches to active branches in company
        self.fields["primary_branch"].queryset = Branch.objects.filter(
            company=self.company,
            is_active=True
        ).order_by("name")

    def clean(self):
        """
        Validate form data with strict company scoping.
        
        Validates:
        - User belongs to the admin's company
        - Branch belongs to the admin's company
        - Branch is active
        """
        cleaned_data = super().clean()
        user = cleaned_data.get("user")
        branch = cleaned_data.get("primary_branch")
        
        if user and branch:
            # Verify user belongs to company
            if user.company_id != self.company.pk:
                raise forms.ValidationError(
                    "Selected user does not belong to your company."
                )
            
            # Verify branch belongs to company
            if branch.company_id != self.company.pk:
                raise forms.ValidationError(
                    "Selected branch does not belong to your company."
                )
            
            # Verify branch is active
            if not branch.is_active:
                raise forms.ValidationError(
                    "Cannot set an inactive branch as primary."
                )
        
        return cleaned_data

    def save(self):
        """
        Execute the primary branch assignment using UserBranch.ensure_primary().
        
        This method:
        1. Extracts validated user and branch
        2. Calls UserBranch.ensure_primary() which atomically:
           - Clears any existing primary flags for this user/company
           - Creates or updates the membership record
           - Sets is_primary=True
        3. Returns the updated membership
        
        Returns:
            UserBranch: The updated primary membership record
        """
        user = self.cleaned_data["user"]
        branch = self.cleaned_data["primary_branch"]
        
        # Use the existing atomic method from UserBranch model
        membership = UserBranch.ensure_primary(
            user=user,
            company=self.company,
            branch=branch
        )
        
        return membership


class BranchManagerAssignmentForm(forms.Form):
    """
    Admin-only form for assigning managers to branches.
    
    Allows administrators to assign or change the primary manager responsible
    for a branch. Enforces company scoping and role validation.
    
    Security:
    - Company-scoped querysets prevent cross-tenant access
    - Only managers and admins can be assigned
    - Validates manager belongs to same company as branch
    - Uses BranchManagerService for atomic operations
    
    Usage:
        form = BranchManagerAssignmentForm(
            request.POST,
            company=request.company,
            admin_user=request.user
        )
        if form.is_valid():
            branch = form.save()
    """
    branch = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Branch",
        help_text="Select the branch to assign a manager to."
    )
    manager = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Manager",
        help_text="Select a manager or admin user to assign to this branch.",
        required=False
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Optional notes about this assignment (e.g., reason for change, handover details)..."
        }),
        label="Assignment Notes",
        required=False,
        help_text="Optional notes about this manager assignment."
    )
    notify_users = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Send Notifications",
        help_text="Notify the current and new managers about this change."
    )

    def __init__(self, *args, **kwargs):
        self.company: Optional[Company] = kwargs.pop("company", None)
        self.admin_user = kwargs.pop("admin_user", None)
        super().__init__(*args, **kwargs)
        
        if self.company is None:
            raise ValueError("Company context is required for BranchManagerAssignmentForm.")
        
        # Scope branches to company - only active branches
        self.fields["branch"].queryset = Branch.objects.filter(
            company=self.company,
            is_active=True
        ).select_related("company", "manager").order_by("name")
        
        # Scope managers to company - only managers and admins
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields["manager"].queryset = User.objects.filter(
            company=self.company,
            is_active=True,
            role__in=['manager', 'admin']
        ).select_related("company").order_by("username")
        
        # Add empty option for removing manager
        self.fields["manager"].empty_label = "-- No Manager (Remove Current) --"

    def clean(self):
        """
        Validate form data with strict company scoping.
        
        Validates:
        - Branch belongs to the admin's company
        - Manager belongs to the admin's company (if provided)
        - Manager has appropriate role
        """
        cleaned_data = super().clean()
        branch = cleaned_data.get("branch")
        manager = cleaned_data.get("manager")
        
        if branch:
            # Verify branch belongs to company
            if branch.company_id != self.company.pk:
                raise forms.ValidationError(
                    "Selected branch does not belong to your company."
                )
        
        if manager:
            # Verify manager belongs to company
            if manager.company_id != self.company.pk:
                raise forms.ValidationError(
                    "Selected manager does not belong to your company."
                )
            
            # Verify manager has appropriate role
            if hasattr(manager, 'role'):
                valid_roles = ['admin', 'manager']
                if manager.role not in valid_roles:
                    raise forms.ValidationError(
                        f"User {manager.username} must have 'manager' or 'admin' role. "
                        f"Current role: {manager.get_role_display()}"
                    )
        
        return cleaned_data

    def save(self):
        """
        Execute the manager assignment using BranchManagerService.
        
        This method:
        1. Extracts validated branch and manager
        2. Calls BranchManagerService.assign_manager() or remove_manager()
        3. Returns the updated branch
        
        Returns:
            Branch: The updated branch instance
        """
        from tenancy.services import BranchManagerService
        
        branch = self.cleaned_data["branch"]
        manager = self.cleaned_data.get("manager")
        notes = self.cleaned_data.get("notes")
        notify_users = self.cleaned_data.get("notify_users", True)
        
        if manager:
            # Assign new manager
            branch = BranchManagerService.assign_manager(
                branch=branch,
                new_manager=manager,
                assigned_by=self.admin_user,
                notes=notes,
                notify_users=notify_users
            )
        else:
            # Remove current manager
            if branch.manager:
                branch = BranchManagerService.remove_manager(
                    branch=branch,
                    removed_by=self.admin_user,
                    reason=notes,
                    notify_user=notify_users
                )
        
        return branch
