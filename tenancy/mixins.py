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
        
        # Branch-scoped roles fail closed. The future Asset Manager and Tenant
        # Admin roles are explicitly tenant-wide; legacy `manager` is not.
        has_branch_field = any(field.name == "branch" for field in qs.model._meta.get_fields())
        if has_branch_field and user and user.is_authenticated:
            from tenancy.access import TENANT_WIDE_ROLES, accessible_branch_ids

            role = getattr(user, 'role', 'user')

            if role in TENANT_WIDE_ROLES:
                if branch:
                    if hasattr(qs, "for_branch"):
                        qs = qs.for_branch(branch)
                    else:
                        qs = qs.filter(branch=branch)
            else:
                authorized_branch_ids = accessible_branch_ids(user, company)
                if branch:
                    if (
                        branch.company_id != getattr(company, 'pk', None)
                        or branch.id not in authorized_branch_ids
                    ):
                        qs = qs.none()
                    else:
                        qs = qs.filter(branch_id=branch.id)
                else:
                    qs = qs.filter(branch_id__in=authorized_branch_ids)
        
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
