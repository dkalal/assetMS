from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from .models import Branch, Company, UserBranch


@dataclass
class TenancyContext:
    company: Optional[Company]
    branch: Optional[Branch]


def resolve_tenancy(request: HttpRequest) -> TenancyContext:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return TenancyContext(company=None, branch=None)

    company = getattr(user, "company", None)
    branch_id = request.session.get("active_branch_id")
    branch: Optional[Branch] = None

    if branch_id:
        branch = (
            Branch.objects.filter(pk=branch_id, company=company, is_active=True)
            .select_related("company")
            .first()
        )
        if branch is None:
            request.session.pop("active_branch_id", None)

    if not company and branch:
        company = branch.company

    if not branch and company:
        membership = (
            UserBranch.objects.select_related("branch")
            .filter(user=user, company=company, is_primary=True, branch__is_active=True)
            .first()
        )
        if membership:
            branch = membership.branch

    return TenancyContext(company=company, branch=branch)


class TenancyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        context = resolve_tenancy(request)
        request.company = context.company
        request.branch = context.branch
        request.available_branches = []

        if getattr(request.user, "is_authenticated", False) and context.company:
            request.available_branches = list(
                UserBranch.objects.select_related("branch")
                .filter(user=request.user, company=context.company, branch__is_active=True)
                .order_by("branch__name")
            )

        require_company = getattr(settings, "TENANCY_REQUIRE_COMPANY_CONTEXT", True)
        exempt_prefixes = getattr(
            settings,
            "TENANCY_COMPANY_EXEMPT_PATH_PREFIXES",
            ("/admin", "/accounts/login", "/accounts/logout", "/healthz", "/status"),
        )

        if (
            require_company
            and getattr(request.user, "is_authenticated", False)
            and not getattr(request.user, "is_system_admin", False)
            and context.company is None
            and not any(request.path.startswith(prefix) for prefix in exempt_prefixes)
        ):
            raise PermissionDenied("Company context required.")

        response = self.get_response(request)
        return response
