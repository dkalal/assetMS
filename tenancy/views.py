from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from django.core.exceptions import ValidationError
from django.db import transaction

from tenancy.mixins import BranchContextMixin, company_required
from tenancy.models import Branch, UserBranch, Alert
from tenancy.forms import BranchForm, CompanyUpdateForm, UserBranchAssignmentForm, BranchManagerAssignmentForm

from audit.utils import log_audit

User = get_user_model()


@login_required
@company_required
def switch_branch(request: HttpRequest) -> HttpResponse:
    branch_id = request.POST.get("branch_id")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("dashboard")

    if not branch_id:
        messages.error(request, "Branch selection is required.")
        return redirect(next_url)

    branch = Branch.objects.filter(pk=branch_id, company=request.company, is_active=True).first()
    if not branch:
        messages.error(request, "Invalid branch selection for your company.")
        return redirect(next_url)

    request.session["active_branch_id"] = branch.pk
    messages.success(request, f"Switched to branch: {branch.name}")
    return redirect(next_url)


class TenantSetupWizardView(LoginRequiredMixin, BranchContextMixin, TemplateView):
    template_name = "tenancy/setup_wizard.html"
    steps = ("company", "branch", "summary")

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not getattr(request.user, "company", None):
            messages.error(request, "Company context required. Contact support.")
            return redirect("dashboard")
        if getattr(request.user, "role", None) != User.ADMIN and not request.user.is_superuser:
            messages.error(request, "You do not have permission to run the tenant setup wizard.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_step(self) -> str:
        step = self.request.GET.get("step") or self.request.POST.get("step") or self.steps[0]
        if step not in self.steps:
            return self.steps[0]
        return step

    @property
    def company(self):
        return getattr(self.request, "company", None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        step = self.get_step()
        step_order = list(self.steps)
        current_index = step_order.index(step)
        company_form = kwargs.get("company_form")
        branch_form = kwargs.get("branch_form")
        if company_form is None and step == "company":
            company_form = self.get_company_form()
        if branch_form is None and step == "branch":
            branch_form = self.get_branch_form()
        steps_context = [
            {
                "slug": slug,
                "label": slug.capitalize(),
                "is_active": idx == current_index,
                "is_completed": idx < current_index,
            }
            for idx, slug in enumerate(step_order)
        ]

        all_branches = Branch.objects.filter(company=self.company).order_by("name") if self.company else Branch.objects.none()
        context.update(
            {
                "current_step": step,
                "steps": step_order,
                "steps_context": steps_context,
                "company_form": company_form,
                "branch_form": branch_form,
                "existing_branches": all_branches,
                "active_branches": all_branches.filter(is_active=True),
                "inactive_branches": all_branches.filter(is_active=False),
                "can_manage_branch_status": BranchStatusToggleView._user_can_manage_branches(self.request.user),
            }
        )
        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        step = self.get_step()
        if step == "company":
            form = self.get_company_form(data=request.POST, files=request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, "Company profile updated.")
                return redirect(self.next_step_url("branch"))
            return self.render_to_response(self.get_context_data(company_form=form))
        if step == "branch":
            form = self.get_branch_form(data=request.POST)
            if form.is_valid():
                branch = form.save(user=request.user)
                if form.cleaned_data.get("set_as_primary"):
                    request.session["active_branch_id"] = branch.pk
                messages.success(request, f"Branch '{branch.name}' saved.")
                return redirect(self.next_step_url("summary"))
            return self.render_to_response(self.get_context_data(branch_form=form))
        return redirect(self.next_step_url("summary"))

    def get(self, request: HttpRequest, *args, **kwargs):
        step = self.get_step()
        if step == "summary" and not Branch.objects.filter(company=self.company, is_active=True).exists():
            messages.info(request, "Add at least one branch to complete setup.")
            return redirect(self.next_step_url("branch"))
        return super().get(request, *args, **kwargs)

    def next_step_url(self, step: str) -> str:
        return f"{reverse('tenant_setup_wizard')}?step={step}"

    def get_company_form(self, data=None, files=None) -> CompanyUpdateForm:
        return CompanyUpdateForm(data=data or None, files=files or None, instance=self.company)

    def get_branch_form(self, data=None) -> BranchForm:
        branch_id = None
        if self.request.method == "POST":
            branch_id = self.request.POST.get("branch_id")
        else:
            branch_id = self.request.GET.get("branch_id")

        branch_instance = None
        if branch_id:
            branch_instance = Branch.objects.filter(company=self.company, pk=branch_id).first()

        return BranchForm(
            data=data or None,
            instance=branch_instance,
            company=self.company,
            user=self.request.user,
        )


class BranchStatusToggleView(LoginRequiredMixin, BranchContextMixin, View):
    success_message_activate = "Branch '{name}' has been reactivated."
    success_message_deactivate = "Branch '{name}' has been deactivated."

    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        company = getattr(request, "company", None)
        if not company:
            messages.error(request, "Company context required to update branch status.")
            return redirect(request.POST.get("next") or reverse("tenant_setup_wizard"))

        if not self._user_can_manage_branches(request.user):
            messages.error(request, "You do not have permission to change branch status.")
            return redirect(request.POST.get("next") or reverse("tenant_setup_wizard"))

        branch = Branch.objects.filter(company=company, pk=pk).first()
        if not branch:
            messages.error(request, "Branch not found for your company.")
            return redirect(request.POST.get("next") or reverse("tenant_setup_wizard"))

        target_state = request.POST.get("target_state")
        if target_state not in {"activate", "deactivate"}:
            messages.error(request, "Unsupported branch status action.")
            return redirect(request.POST.get("next") or reverse("tenant_setup_wizard"))

        desired_active = target_state == "activate"
        if branch.is_active == desired_active:
            messages.info(request, f"Branch '{branch.name}' is already in the desired state.")
            return redirect(request.POST.get("next") or reverse("tenant_setup_wizard"))

        with transaction.atomic():
            branch.is_active = desired_active
            try:
                branch.full_clean()
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
                return redirect(request.POST.get("next") or reverse("tenant_setup_wizard"))

            branch.save(update_fields=["is_active", "updated_at"])

            if not desired_active:
                UserBranch.objects.filter(branch=branch, is_primary=True).update(is_primary=False)
                if request.session.get("active_branch_id") == branch.pk:
                    request.session.pop("active_branch_id", None)

            action = "branch_activated" if desired_active else "branch_deactivated"
            log_audit(
                request.user,
                action,
                details=f"Branch '{branch.name}' status set to {'active' if desired_active else 'inactive' }.",
                company=company,
                branch=branch
            )

            recipients = list(
                User.objects.filter(
                    company=company,
                    role__in=[User.ADMIN, User.MANAGER],
                )
            )
            if recipients:
                level = Alert.LEVEL_SUCCESS if desired_active else Alert.LEVEL_WARNING
                message = (
                    f"Branch '{branch.name}' has been reactivated." if desired_active
                    else f"Branch '{branch.name}' has been deactivated."
                )
                context = {
                    "branch_id": branch.pk,
                    "branch_code": branch.code,
                    "is_active": branch.is_active,
                    "updated_by": request.user.pk,
                }
                Alert.objects.bulk_create(
                    [
                        Alert(
                            company=company,
                            branch=branch,
                            recipient=recipient,
                            level=level,
                            message=message,
                            context=context,
                        )
                        for recipient in recipients
                    ]
                )

        success_message = (
            self.success_message_activate if desired_active else self.success_message_deactivate
        )
        messages.success(request, success_message.format(name=branch.name))
        return redirect(request.POST.get("next") or reverse("tenant_setup_wizard"))

    @staticmethod
    def _user_can_manage_branches(user) -> bool:
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return getattr(user, "role", None) == getattr(user.__class__, "ADMIN", "admin")


class UserBranchManagementView(LoginRequiredMixin, BranchContextMixin, TemplateView):
    """
    Admin-only view for managing user-branch primary assignments.
    
    This view provides a professional interface for administrators to:
    - View all company users and their current primary branches
    - Assign or change primary branches for any user
    - See all branch memberships for each user
    
    Security:
    - Restricted to users with ADMIN role or superuser status
    - All queries scoped to request.company
    - CSRF protection via Django middleware
    - Audit logging for all changes
    - Alert notifications sent to affected users
    
    URL: /tenancy/user-branches/
    Template: tenancy/user_branch_management.html
    """
    template_name = "tenancy/user_branch_management.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Enforce admin-only access before processing any requests."""
        # Ensure company context exists
        if not getattr(request, "company", None):
            messages.error(request, "Company context required.")
            return redirect("dashboard")
        
        # Enforce admin role or superuser
        user_role = getattr(request.user, "role", None)
        is_admin = user_role == getattr(request.user.__class__, "ADMIN", "admin")
        
        if not is_admin and not request.user.is_superuser:
            messages.error(
                request,
                "You do not have permission to manage user branch assignments."
            )
            return redirect("dashboard")
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Prepare context data for template rendering.
        
        Returns:
            dict: Context containing users_data, form, active_branches, etc.
        """
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "company", None)
        
        # Get all users with their primary branches
        users_data = []
        users = User.objects.filter(
            company=company,
            is_active=True
        ).select_related("company").order_by("username")
        
        for user in users:
            # Get primary branch membership
            primary_membership = UserBranch.objects.filter(
                user=user,
                company=company,
                is_primary=True
            ).select_related("branch").first()
            
            # Get all branch memberships
            all_memberships = UserBranch.objects.filter(
                user=user,
                company=company,
                branch__is_active=True
            ).select_related("branch").order_by("branch__name")
            
            users_data.append({
                "user": user,
                "primary_branch": primary_membership.branch if primary_membership else None,
                "all_branches": all_memberships,
                "membership_count": all_memberships.count()
            })
        
        context.update({
            "users_data": users_data,
            "form": UserBranchAssignmentForm(
                company=company,
                admin_user=self.request.user
            ),
            "active_branches": Branch.objects.filter(
                company=company,
                is_active=True
            ).order_by("name"),
            "total_users": len(users_data),
        })
        
        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        """
        Handle form submission for primary branch assignment.
        
        Process:
        1. Validate form data
        2. Save the primary branch assignment
        3. Log audit event
        4. Create alert notification for affected user
        5. Display success message
        6. Redirect to refresh the page
        
        Returns:
            HttpResponse: Redirect on success, re-render on validation error
        """
        company = getattr(request, "company", None)
        form = UserBranchAssignmentForm(
            request.POST,
            company=company,
            admin_user=request.user
        )
        
        if form.is_valid():
            with transaction.atomic():
                # Save the primary branch assignment
                membership = form.save()
                
                # Log comprehensive audit event
                log_audit(
                    request.user,
                    "user_primary_branch_updated",
                    details=(
                        f"Admin {request.user.username} set primary branch "
                        f"'{membership.branch.name}' for user '{membership.user.username}'."
                    ),
                    company=company,
                    branch=membership.branch,
                    related_user=membership.user,
                    metadata={
                        "admin_id": request.user.pk,
                        "admin_username": request.user.username,
                        "target_user_id": membership.user.pk,
                        "target_username": membership.user.username,
                        "branch_id": membership.branch.pk,
                        "branch_name": membership.branch.name,
                        "branch_code": membership.branch.code,
                    }
                )
                
                # Create alert notification for the affected user
                from django.utils import timezone
                Alert.objects.create(
                    company=company,
                    branch=membership.branch,
                    recipient=membership.user,
                    level=Alert.LEVEL_INFO,
                    message=(
                        f"Your primary branch has been updated to '{membership.branch.name}' "
                        f"by {request.user.get_full_name() or request.user.username}."
                    ),
                    context={
                        "branch_id": membership.branch.pk,
                        "branch_name": membership.branch.name,
                        "branch_code": membership.branch.code,
                        "updated_by": request.user.pk,
                        "updated_by_name": request.user.get_full_name() or request.user.username,
                        "timestamp": timezone.now().isoformat(),
                    }
                )
            
            # Success message
            messages.success(
                request,
                f"Successfully set '{membership.branch.name}' as primary branch for "
                f"{membership.user.get_full_name() or membership.user.username}."
            )
            return redirect("user_branch_management")
        
        # Form invalid - re-render with errors
        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)


class BranchManagerManagementView(LoginRequiredMixin, BranchContextMixin, TemplateView):
    """
    Admin-only view for managing branch manager assignments.
    
    This view provides a professional interface for administrators to:
    - View all branches and their assigned managers
    - Assign or change managers for branches
    - Remove managers from branches
    - View manager performance statistics
    
    Security:
    - Restricted to users with ADMIN role or superuser status
    - All queries scoped to request.company
    - CSRF protection via Django middleware
    - Audit logging for all changes
    - Alert notifications sent to affected managers
    
    URL: /tenancy/branch-managers/
    Template: tenancy/branch_manager_management.html
    """
    template_name = "tenancy/branch_manager_management.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Enforce admin-only access before processing any requests."""
        # Ensure company context exists
        if not getattr(request, "company", None):
            messages.error(request, "Company context required.")
            return redirect("dashboard")
        
        # Enforce admin role or superuser
        user_role = getattr(request.user, "role", None)
        is_admin = user_role == getattr(request.user.__class__, "ADMIN", "admin")
        
        if not is_admin and not request.user.is_superuser:
            messages.error(
                request,
                "You do not have permission to manage branch manager assignments."
            )
            return redirect("dashboard")
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Prepare context data for template rendering.
        
        Returns:
            dict: Context containing branches_data, form, available_managers, etc.
        """
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "company", None)
        
        # Get all branches with their managers
        branches_data = []
        branches = Branch.objects.filter(
            company=company,
            is_active=True
        ).select_related("company", "manager", "manager_assigned_by").order_by("name")
        
        for branch in branches:
            # Get asset count for this branch
            from assets.models import Asset
            asset_count = Asset.objects.filter(branch=branch, company=company).count()
            
            # Get staff count for this branch
            staff_count = User.objects.filter(
                user_branches__branch=branch,
                company=company,
                is_active=True
            ).distinct().count()
            
            branches_data.append({
                "branch": branch,
                "manager": branch.manager,
                "manager_assigned_at": branch.manager_assigned_at,
                "manager_assigned_by": branch.manager_assigned_by,
                "asset_count": asset_count,
                "staff_count": staff_count,
                "has_manager": branch.manager is not None,
            })
        
        # Get available managers
        available_managers = User.objects.filter(
            company=company,
            is_active=True,
            role__in=['manager', 'admin']
        ).select_related("company").order_by("username")
        
        # Get manager statistics
        manager_stats = []
        for manager in available_managers:
            from tenancy.services import BranchManagerService
            stats = BranchManagerService.get_manager_statistics(manager, company)
            manager_stats.append(stats)
        
        context.update({
            "branches_data": branches_data,
            "form": BranchManagerAssignmentForm(
                company=company,
                admin_user=self.request.user
            ),
            "available_managers": available_managers,
            "manager_stats": manager_stats,
            "total_branches": len(branches_data),
            "branches_with_managers": sum(1 for b in branches_data if b["has_manager"]),
            "branches_without_managers": sum(1 for b in branches_data if not b["has_manager"]),
        })
        
        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        """
        Handle form submission for branch manager assignment.
        
        Process:
        1. Validate form data
        2. Save the manager assignment (via BranchManagerService)
        3. Display success message
        4. Redirect to refresh the page
        
        Returns:
            HttpResponse: Redirect on success, re-render on validation error
        """
        company = getattr(request, "company", None)
        form = BranchManagerAssignmentForm(
            request.POST,
            company=company,
            admin_user=request.user
        )
        
        if form.is_valid():
            try:
                branch = form.save()
                
                # Success message
                if branch.manager:
                    messages.success(
                        request,
                        f"Successfully assigned {branch.manager.get_full_name() or branch.manager.username} "
                        f"as manager of '{branch.name}'."
                    )
                else:
                    messages.success(
                        request,
                        f"Successfully removed manager from '{branch.name}'."
                    )
                return redirect("branch_manager_management")
            except ValidationError as e:
                messages.error(request, str(e))
        
        # Form invalid - re-render with errors
        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)
