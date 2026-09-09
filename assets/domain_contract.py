"""Stable Phase 0B domain contract for the AssetMS redesign.

This module is intentionally persistence-free.  Phase 1 migrations may map these
names to database fields, but Phase 0B uses the contract to make lifecycle, RBAC,
identifier, retention, and offline decisions executable and reviewable first.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType


class StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class AssetState(StringEnum):
    DRAFT = "draft"
    AVAILABLE = "available"
    PENDING_ACCEPTANCE = "pending_acceptance"
    ASSIGNED = "assigned"
    INSPECTION_REQUIRED = "inspection_required"
    IN_MAINTENANCE = "in_maintenance"
    LOST = "lost"
    RETIRED = "retired"
    DISPOSAL_PENDING = "disposal_pending"
    DISPOSED = "disposed"


TERMINAL_ASSET_STATES = frozenset({AssetState.DISPOSED})

ASSET_TRANSITIONS = MappingProxyType(
    {
        AssetState.DRAFT: frozenset({AssetState.AVAILABLE, AssetState.PENDING_ACCEPTANCE}),
        AssetState.AVAILABLE: frozenset(
            {
                AssetState.PENDING_ACCEPTANCE,
                AssetState.IN_MAINTENANCE,
                AssetState.LOST,
                AssetState.RETIRED,
            }
        ),
        AssetState.PENDING_ACCEPTANCE: frozenset(
            {AssetState.ASSIGNED, AssetState.AVAILABLE}
        ),
        AssetState.ASSIGNED: frozenset(
            {
                AssetState.INSPECTION_REQUIRED,
                AssetState.IN_MAINTENANCE,
                AssetState.LOST,
                AssetState.RETIRED,
            }
        ),
        AssetState.INSPECTION_REQUIRED: frozenset(
            {AssetState.AVAILABLE, AssetState.IN_MAINTENANCE, AssetState.RETIRED}
        ),
        AssetState.IN_MAINTENANCE: frozenset(
            {
                AssetState.AVAILABLE,
                AssetState.ASSIGNED,
                AssetState.INSPECTION_REQUIRED,
                AssetState.RETIRED,
            }
        ),
        AssetState.LOST: frozenset({AssetState.INSPECTION_REQUIRED, AssetState.RETIRED}),
        AssetState.RETIRED: frozenset(
            {AssetState.INSPECTION_REQUIRED, AssetState.DISPOSAL_PENDING}
        ),
        AssetState.DISPOSAL_PENDING: frozenset(
            {AssetState.RETIRED, AssetState.DISPOSED}
        ),
        AssetState.DISPOSED: frozenset(),
    }
)


class MaintenanceState(StringEnum):
    REQUESTED = "requested"
    TRIAGED = "triaged"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    CLOSED = "closed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Role(StringEnum):
    PLATFORM_SUPER_ADMIN = "platform_super_admin"
    TENANT_ADMIN = "tenant_admin"
    ASSET_MANAGER = "asset_manager"
    BRANCH_MANAGER = "branch_manager"
    TECHNICIAN = "technician"
    CUSTODIAN = "custodian"


class DataScope(StringEnum):
    PLATFORM_SUPPORT_SESSION = "platform_support_session"
    TENANT = "tenant"
    ASSIGNED_BRANCHES = "assigned_branches"
    ASSIGNED_WORK = "assigned_work"
    SELF = "self"


ROLE_SCOPES = MappingProxyType(
    {
        Role.PLATFORM_SUPER_ADMIN: DataScope.PLATFORM_SUPPORT_SESSION,
        Role.TENANT_ADMIN: DataScope.TENANT,
        Role.ASSET_MANAGER: DataScope.TENANT,
        Role.BRANCH_MANAGER: DataScope.ASSIGNED_BRANCHES,
        Role.TECHNICIAN: DataScope.ASSIGNED_WORK,
        Role.CUSTODIAN: DataScope.SELF,
    }
)


class Permission(StringEnum):
    ASSET_VIEW = "asset.view"
    ASSET_REQUEST = "asset.request"
    ASSET_APPROVE_REQUEST = "asset.approve_request"
    ASSET_REGISTER = "asset.register"
    ASSET_ASSIGN = "asset.assign"
    ASSET_REPORT_LOST = "asset.report_lost"
    ASSET_RETIRE = "asset.retire"
    ASSET_REQUEST_DISPOSAL = "asset.request_disposal"
    ASSET_APPROVE_DISPOSAL = "asset.approve_disposal"
    MAINTENANCE_REQUEST = "maintenance.request"
    MAINTENANCE_MANAGE = "maintenance.manage"
    MAINTENANCE_VERIFY = "maintenance.verify"
    STOCKTAKE_PERFORM = "stocktake.perform"
    TENANT_MANAGE_USERS = "tenant.manage_users"
    TENANT_MANAGE_SETTINGS = "tenant.manage_settings"
    AUDIT_VIEW = "audit.view"
    EXPORT_RUN = "export.run"


ROLE_PERMISSION_BASELINES = MappingProxyType(
    {
        Role.PLATFORM_SUPER_ADMIN: frozenset(),
        Role.TENANT_ADMIN: frozenset(Permission),
        Role.ASSET_MANAGER: frozenset(
            {
                Permission.ASSET_VIEW,
                Permission.ASSET_REQUEST,
                Permission.ASSET_APPROVE_REQUEST,
                Permission.ASSET_REGISTER,
                Permission.ASSET_ASSIGN,
                Permission.ASSET_REPORT_LOST,
                Permission.ASSET_RETIRE,
                Permission.ASSET_REQUEST_DISPOSAL,
                Permission.MAINTENANCE_REQUEST,
                Permission.MAINTENANCE_MANAGE,
                Permission.MAINTENANCE_VERIFY,
                Permission.STOCKTAKE_PERFORM,
                Permission.AUDIT_VIEW,
                Permission.EXPORT_RUN,
            }
        ),
        Role.BRANCH_MANAGER: frozenset(
            {
                Permission.ASSET_VIEW,
                Permission.ASSET_REQUEST,
                Permission.ASSET_APPROVE_REQUEST,
                Permission.ASSET_REGISTER,
                Permission.ASSET_ASSIGN,
                Permission.ASSET_REPORT_LOST,
                Permission.ASSET_REQUEST_DISPOSAL,
                Permission.MAINTENANCE_REQUEST,
                Permission.MAINTENANCE_MANAGE,
                Permission.MAINTENANCE_VERIFY,
                Permission.STOCKTAKE_PERFORM,
            }
        ),
        Role.TECHNICIAN: frozenset(
            {
                Permission.ASSET_VIEW,
                Permission.ASSET_REPORT_LOST,
                Permission.MAINTENANCE_REQUEST,
                Permission.MAINTENANCE_MANAGE,
                Permission.STOCKTAKE_PERFORM,
            }
        ),
        Role.CUSTODIAN: frozenset(
            {
                Permission.ASSET_VIEW,
                Permission.ASSET_REQUEST,
                Permission.ASSET_REPORT_LOST,
                Permission.MAINTENANCE_REQUEST,
            }
        ),
    }
)


IDENTIFIER_POLICY = MappingProxyType(
    {
        "manufacturer_serial": "unique_per_tenant_forever_when_present",
        "asset_tag": "unique_per_tenant_forever_when_present",
        "qr_token": "opaque_random_globally_unique_rotatable",
        "numeric_database_id_public": False,
        "similarity_warning_blocks_save": False,
        "duplicate_within_bulk_file_blocks_import": True,
    }
)

AUDIT_RETENTION_POLICY = MappingProxyType(
    {
        "business_lifecycle": "tenant_lifetime_plus_legal_hold",
        "approval_and_custody": "tenant_lifetime_plus_legal_hold",
        "authentication_and_security_default_days": 365,
        "authentication_and_security_minimum_days": 90,
    }
)

OFFLINE_CONFLICT_POLICY = MappingProxyType(
    {
        "server_is_source_of_truth": True,
        "write_precondition": "entity_version_or_etag",
        "retry_identity": "idempotency_key",
        "custody_conflict": "supervisor_resolution_queue",
        "lifecycle_conflict": "supervisor_resolution_queue",
        "never_use_blind_last_write_wins": True,
    }
)


def can_transition(current: AssetState, target: AssetState) -> bool:
    """Return whether the target is an allowed direct lifecycle transition."""

    return target in ASSET_TRANSITIONS[current]


def validate_contract() -> None:
    """Raise ``ValueError`` when the architecture contract is internally invalid."""

    states = set(AssetState)
    if set(ASSET_TRANSITIONS) != states:
        raise ValueError("Every asset state must have an explicit transition set.")
    unknown_targets = set().union(*ASSET_TRANSITIONS.values()) - states
    if unknown_targets:
        raise ValueError(f"Unknown lifecycle targets: {sorted(unknown_targets)}")
    if set(ROLE_SCOPES) != set(Role):
        raise ValueError("Every fixed role must have one explicit data scope.")
    if set(ROLE_PERMISSION_BASELINES) != set(Role):
        raise ValueError("Every fixed role must have a permission baseline.")
    if ROLE_PERMISSION_BASELINES[Role.PLATFORM_SUPER_ADMIN]:
        raise ValueError("Platform admins must not receive implicit tenant permissions.")
