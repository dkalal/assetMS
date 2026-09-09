"""Fail-closed tenant and branch access helpers.

These helpers operate on the current schema while preserving the Phase 0B
contract. Phase 1 will replace the legacy ``User.company``/``User.role`` inputs
with tenant memberships without changing these authorization semantics.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied


TENANT_WIDE_ROLES = frozenset({"admin", "tenant_admin", "asset_manager"})
BRANCH_SCOPED_ROLES = frozenset(
    {"manager", "branch_manager", "technician", "user", "custodian"}
)


def require_user_company(user, company) -> None:
    """Require an authenticated user whose tenant matches ``company``."""

    if not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication is required.")
    company_id = getattr(company, "pk", company)
    if company_id is None or getattr(user, "company_id", None) != company_id:
        raise PermissionDenied("Tenant context does not match the authenticated user.")


def accessible_branch_ids(user, company) -> frozenset[int]:
    """Return authorized active branch IDs, never a permissive fallback.

    Legacy ``manager`` maps to the future Branch Manager role. Its scope is the
    union of explicit UserBranch grants and branches it manages. No assignments
    means no branch access. Platform/system superuser flags are intentionally
    not tenant authorization.
    """

    try:
        require_user_company(user, company)
    except PermissionDenied:
        return frozenset()

    from tenancy.models import Branch, UserBranch

    role = getattr(user, "role", "")
    if role in TENANT_WIDE_ROLES:
        return frozenset(
            Branch.objects.filter(company=company, is_active=True).values_list(
                "id", flat=True
            )
        )
    if role not in BRANCH_SCOPED_ROLES:
        return frozenset()

    branch_ids = set(
        UserBranch.objects.filter(
            user=user,
            company=company,
            branch__is_active=True,
        ).values_list("branch_id", flat=True)
    )
    if role in {"manager", "branch_manager"}:
        branch_ids.update(
            Branch.objects.filter(
                company=company,
                manager=user,
                is_active=True,
            ).values_list("id", flat=True)
        )
    return frozenset(branch_ids)
