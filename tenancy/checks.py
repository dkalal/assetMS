"""Django system checks for non-negotiable tenant isolation structure."""

from django.apps import apps
from django.core.checks import Error, Tags, register
from django.core.exceptions import FieldDoesNotExist


TENANT_MODELS = (
    "assets.Asset",
    "assets.AssetCategory",
    "assets.AssetCategoryField",
    "assets.AssetTransfer",
    "tenancy.ApprovalRequest",
    "tenancy.Branch",
    "tenancy.UserBranch",
    "audit.AuditLog",
    "audit.AuditEvent",
)

SCOPED_MANAGER_MODELS = (
    "assets.Asset",
    "assets.AssetCategory",
    "assets.AssetCategoryField",
    "tenancy.ApprovalRequest",
    "tenancy.Branch",
)

# AuditLog predates strict tenant ownership and contains platform-era rows.
# Phase 1 must backfill it before changing the field to non-null.
NULLABLE_COMPANY_PHASE_0_EXCEPTIONS = frozenset({"audit.AuditLog"})


@register(Tags.security)
def tenant_isolation_structure_check(app_configs, **kwargs):
    errors = []
    for model_label in TENANT_MODELS:
        model = apps.get_model(model_label)
        try:
            company_field = model._meta.get_field("company")
        except FieldDoesNotExist:
            errors.append(
                Error(
                    f"{model_label} has no tenant key.",
                    id="assetms_security.E001",
                )
            )
            continue
        if company_field.null and model_label not in NULLABLE_COMPANY_PHASE_0_EXCEPTIONS:
            errors.append(
                Error(
                    f"{model_label}.company must fail closed and cannot be nullable.",
                    id="assetms_security.E002",
                )
            )

    for model_label in SCOPED_MANAGER_MODELS:
        model = apps.get_model(model_label)
        if not hasattr(model._default_manager.all(), "for_company"):
            errors.append(
                Error(
                    f"{model_label}'s default queryset has no for_company() scope.",
                    id="assetms_security.E003",
                )
            )
    return errors
