from __future__ import annotations

from typing import Any, Callable, Iterable

from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache


class CompanyRequiredMixin:
    """Ensure a request-scoped company is available before dispatching."""

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request, "company", None):
            raise PermissionDenied("Company context required.")
        return super().dispatch(request, *args, **kwargs)


class BranchContextMixin(CompanyRequiredMixin):
    """Expose helper attributes for templates needing branch lists."""

    def get_context_data(self, **kwargs: Any) -> dict:
        try:
            context = super().get_context_data(**kwargs)  # type: ignore[misc]
        except AttributeError:
            context = {}
            context.update(kwargs)
        context.setdefault("company", getattr(self.request, "company", None))
        context.setdefault("active_branch", getattr(self.request, "branch", None))
        context.setdefault("available_branches", getattr(self.request, "available_branches", []))
        return context


class CompanyScopedQuerysetMixin(CompanyRequiredMixin):
    queryset_select_related: Iterable[str] = ()
    queryset_prefetch_related: Iterable[str] = ()

    def get_company(self):
        return getattr(self.request, "company", None)

    def get_branch(self):
        return getattr(self.request, "branch", None)

    def get_queryset(self):
        qs = super().get_queryset()
        company = self.get_company()
        branch = self.get_branch()
        user = getattr(self.request, 'user', None)
        
        # Company scoping
        if hasattr(qs, "for_company"):
            qs = qs.for_company(company)
        else:
            qs = qs.filter(company=company)
        
        # Branch scoping - enforce policy-driven multi-tenancy
        has_branch_field = any(field.name == "branch" for field in qs.model._meta.get_fields())
        if has_branch_field and user and user.is_authenticated:
            from tenancy.policy_service import policy_service
            
            role = getattr(user, 'role', 'user')
            
            # Admins always see all company assets (bypass branch restrictions)
            if role == 'admin':
                # If a specific branch is selected, filter by it
                if branch:
                    if hasattr(qs, "for_branch"):
                        qs = qs.for_branch(branch)
                    else:
                        qs = qs.filter(branch=branch)
            # Managers and users: check if branch-level access is enforced
            else:
                # Check company policy for branch-level access enforcement
                should_enforce = policy_service.should_enforce_branch_scoping(user, company)
                
                if should_enforce:
                    # Enforce branch-level access control
                    from tenancy.models import UserBranch
                    user_branches = UserBranch.objects.filter(
                        user=user, 
                        company=company,
                        branch__is_active=True
                    ).values_list('branch_id', flat=True)
                    
                    if user_branches:
                        # If a specific branch is selected and user has access to it, use it
                        if branch and branch.id in user_branches:
                            qs = qs.filter(branch=branch)
                        else:
                            # Otherwise, show assets from all branches user has access to
                            qs = qs.filter(branch_id__in=user_branches)
                    else:
                        # User has no branch assignments - show nothing
                        qs = qs.none()
                else:
                    # Branch-level access disabled: managers/users see all company data
                    if branch:
                        if hasattr(qs, "for_branch"):
                            qs = qs.for_branch(branch)
                        else:
                            qs = qs.filter(branch=branch)
        
        if self.queryset_select_related:
            qs = qs.select_related(*self.queryset_select_related)
        if self.queryset_prefetch_related:
            qs = qs.prefetch_related(*self.queryset_prefetch_related)
        return qs


def company_required(view_func: Callable) -> Callable:
    @never_cache
    def _wrapped(request, *args, **kwargs):
        if not getattr(request, "company", None):
            raise PermissionDenied("Company context required.")
        return view_func(request, *args, **kwargs)

    return _wrapped
