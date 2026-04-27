from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import CharField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date
from django.utils import timezone
from weasyprint import HTML

from assets.models import Asset, AssetTransfer, MaintenanceRecord
from audit.models import AuditLog


@dataclass
class ReportFilters:
    status: Optional[str] = None
    branch_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    user_id: Optional[int] = None

    def cache_key_suffix(self) -> str:
        payload = (
            f"status={self.status}|branch={self.branch_id}|from={self.date_from}|"
            f"to={self.date_to}|user={self.user_id}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_available_individual_report_users(company, user):
    """Return tenant-scoped users the requester may include in individual reports."""
    from tenancy.models import UserBranch
    from tenancy.policy_service import PolicyService

    User = get_user_model()
    primary_branch_name = UserBranch.objects.filter(
        user=OuterRef("pk"),
        company=company,
        is_primary=True,
    ).values("branch__name")[:1]

    users = User.objects.filter(company=company).annotate(
        report_branch_label=Coalesce(
            Subquery(primary_branch_name),
            Value("No primary branch"),
            output_field=CharField(),
        )
    ).order_by("first_name", "last_name", "username")

    if getattr(user, "role", None) == "admin":
        return users

    accessible_branch_ids = list(PolicyService.get_accessible_branches(user, company))
    if not accessible_branch_ids:
        return users.none()

    return users.filter(
        user_branches__branch_id__in=accessible_branch_ids,
        user_branches__company=company,
    ).distinct()


def attach_report_branch_labels(users, company):
    """Attach a display-only branch list to report users without changing access rules."""
    from tenancy.models import UserBranch

    users_list = list(users)
    user_ids = [user.pk for user in users_list]
    if not user_ids:
        return users_list

    memberships = (
        UserBranch.objects.filter(company=company, user_id__in=user_ids)
        .select_related("branch")
        .order_by("-is_primary", "branch__name")
    )

    labels_by_user = {user_id: [] for user_id in user_ids}
    branch_ids_by_user = {user_id: [] for user_id in user_ids}
    for membership in memberships:
        if membership.branch and membership.branch.is_active:
            labels_by_user.setdefault(membership.user_id, []).append(membership.branch.name)
            branch_ids_by_user.setdefault(membership.user_id, []).append(str(membership.branch_id))

    for user in users_list:
        branches = labels_by_user.get(user.pk) or []
        user.report_branch_label = ", ".join(branches) if branches else "No branch assigned"
        user.report_branch_ids = ",".join(branch_ids_by_user.get(user.pk) or [])

    return users_list


def validate_report_filters(filters: ReportFilters) -> Optional[str]:
    """Validate shared report filters before preview or file generation."""
    start = parse_date(filters.date_from) if filters.date_from else None
    end = parse_date(filters.date_to) if filters.date_to else None

    if filters.date_from and start is None:
        return "Invalid start date. Please use a valid date."
    if filters.date_to and end is None:
        return "Invalid end date. Please use a valid date."
    if start and end and start > end:
        return "Start date cannot be after end date."
    return None


def user_can_access_report_branch(company, user, branch) -> bool:
    if branch is None or getattr(user, "role", None) == "admin":
        return True
    from tenancy.policy_service import PolicyService

    accessible_branch_ids = set(PolicyService.get_accessible_branches(user, company))
    return branch.pk in accessible_branch_ids


def fetch_assets(company, branch, filters: ReportFilters) -> List[Asset]:
    queryset = Asset.objects.select_related("category", "assigned_to", "branch").filter(company=company)
    if branch:
        queryset = queryset.filter(branch=branch)
    if filters.status:
        queryset = queryset.filter(status=filters.status)
    if filters.branch_id:
        queryset = queryset.filter(branch_id=filters.branch_id)
    if filters.date_from:
        queryset = queryset.filter(created_at__date__gte=filters.date_from)
    if filters.date_to:
        queryset = queryset.filter(created_at__date__lte=filters.date_to)
    return list(queryset.order_by("-created_at"))


def fetch_assets_cached(company, branch, filters: ReportFilters, ttl: int = 300) -> List[Asset]:
    cache_key = f"report_assets:{company.id}:{getattr(branch, 'id', 'all')}:{filters.cache_key_suffix()}"
    assets = cache.get(cache_key)
    if assets is None:
        assets = fetch_assets(company, branch, filters)
        cache.set(cache_key, assets, ttl)
    return assets


def render_assets_dataframe(assets: Iterable[Asset]) -> pd.DataFrame:
    base_columns = [
        "ID",
        "UUID",
        "Category",
        "Status",
        "Branch",
        "Assigned To",
        "Created",
        "Updated",
    ]
    dynamic_keys: set[str] = set()
    rows: List[Dict[str, object]] = []

    for asset in assets:
        row: Dict[str, object] = {
            "ID": asset.pk,
            "UUID": str(asset.uuid),
            "Category": asset.category.name,
            "Status": asset.get_status_display() if hasattr(asset, "get_status_display") else asset.status,
            "Branch": asset.branch.name if asset.branch else "Head Office",
            "Assigned To": str(asset.assigned_to) if asset.assigned_to else "",
            "Created": asset.created_at.strftime("%Y-%m-%d %H:%M"),
            "Updated": asset.updated_at.strftime("%Y-%m-%d %H:%M"),
        }
        for key, value in (asset.dynamic_data or {}).items():
            normalized_key = key.replace("_", " ").title()
            row[normalized_key] = value if isinstance(value, (int, float)) else str(value)
            dynamic_keys.add(normalized_key)
        rows.append(row)

    all_columns = base_columns + sorted(dynamic_keys)
    if not rows:
        return pd.DataFrame(columns=all_columns)

    normalized_rows: List[Dict[str, object]] = []
    for row in rows:
        normalized_row = {column: row.get(column, "") for column in all_columns}
        normalized_rows.append(normalized_row)

    return pd.DataFrame(normalized_rows, columns=all_columns)


def build_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    engine = None
    try:
        import xlsxwriter  # noqa: F401
        engine = "xlsxwriter"
    except Exception:
        try:
            import openpyxl  # noqa: F401
            engine = "openpyxl"
        except Exception:
            engine = None

    if engine:
        with pd.ExcelWriter(buffer, engine=engine) as writer:
            df.to_excel(writer, index=False, sheet_name="Assets")
    else:
        with pd.ExcelWriter(buffer) as writer:
            df.to_excel(writer, index=False, sheet_name="Assets")
    return buffer.getvalue()


def build_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def build_pdf_bytes(assets: Iterable[Asset], metadata: Dict[str, object]) -> bytes:
    assets_list = list(assets)
    dynamic_columns: list[str] = []
    seen: set[str] = set()
    for a in assets_list:
        for k in (getattr(a, "dynamic_data", None) or {}).keys():
            if k not in seen:
                seen.add(k)
                dynamic_columns.append(k)

    ctx = {
        "assets": assets_list,
        "metadata": metadata,
        "dynamic_columns": sorted(dynamic_columns),
    }
    html_string = render_to_string("reports/asset_summary_pdf.html", ctx)
    buffer = io.BytesIO()
    HTML(string=html_string, base_url=metadata.get("base_url")).write_pdf(buffer)
    return buffer.getvalue()


def _display_user(user) -> str:
    if not user:
        return ""
    return user.get_full_name() or user.username


def _asset_display_name(asset: Asset) -> str:
    data = asset.dynamic_data or {}
    return (
        data.get("name")
        or data.get("asset_name")
        or asset.asset_tag
        or asset.serial_number
        or f"{asset.category.name} #{asset.pk}"
    )


def _parse_money(raw) -> Decimal:
    if raw in (None, ""):
        return Decimal("0")
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    if isinstance(raw, str):
        cleaned = "".join(ch for ch in raw if ch.isdigit() or ch in ".-")
        if cleaned in ("", ".", "-", "-."):
            return Decimal("0")
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return Decimal("0")
    return Decimal("0")


def _asset_value(asset: Asset) -> Decimal:
    data = asset.dynamic_data or {}
    for key in ("current_value", "book_value", "net_value", "purchase_value", "purchase_price", "price", "value", "cost"):
        value = data.get(key)
        if value not in (None, ""):
            return _parse_money(value)
    return Decimal("0")


def fetch_individual_report_data(company, subject_user, filters: ReportFilters, branch=None) -> Dict[str, object]:
    """Build a company-scoped, person-specific report payload."""
    assets_qs = (
        Asset.objects.filter(company=company, assigned_to=subject_user)
        .exclude(status=Asset.STATUS_DELETED)
        .select_related("category", "branch", "assigned_to")
        .order_by("category__name", "asset_tag", "-created_at")
    )
    if branch:
        assets_qs = assets_qs.filter(branch=branch)
    if filters.status:
        assets_qs = assets_qs.filter(status=filters.status)
    if filters.date_from:
        assets_qs = assets_qs.filter(created_at__date__gte=filters.date_from)
    if filters.date_to:
        assets_qs = assets_qs.filter(created_at__date__lte=filters.date_to)

    assets = list(assets_qs)
    asset_ids = [asset.pk for asset in assets]

    transfers_qs = (
        AssetTransfer.objects.filter(company=company)
        .filter(Q(from_user=subject_user) | Q(to_user=subject_user))
        .select_related("asset", "asset__category", "from_user", "to_user", "initiator", "approved_by")
        .order_by("-created_at")
    )
    if branch:
        transfers_qs = transfers_qs.filter(Q(from_branch=branch) | Q(to_branch=branch))
    if filters.date_from:
        transfers_qs = transfers_qs.filter(created_at__date__gte=filters.date_from)
    if filters.date_to:
        transfers_qs = transfers_qs.filter(created_at__date__lte=filters.date_to)

    maintenance_qs = (
        MaintenanceRecord.objects.filter(company=company, asset_id__in=asset_ids)
        .select_related("asset", "asset__category", "branch", "performed_by", "supervisor")
        .order_by("-scheduled_for", "-created_at")
    )
    if branch:
        maintenance_qs = maintenance_qs.filter(branch=branch)
    if filters.date_from:
        maintenance_qs = maintenance_qs.filter(scheduled_for__gte=filters.date_from)
    if filters.date_to:
        maintenance_qs = maintenance_qs.filter(scheduled_for__lte=filters.date_to)

    activities_qs = (
        AuditLog.objects.filter(company=company, user=subject_user)
        .select_related("asset", "branch")
        .order_by("-timestamp")
    )
    if branch:
        activities_qs = activities_qs.filter(branch=branch)
    if filters.date_from:
        activities_qs = activities_qs.filter(timestamp__date__gte=filters.date_from)
    if filters.date_to:
        activities_qs = activities_qs.filter(timestamp__date__lte=filters.date_to)

    active_count = sum(1 for asset in assets if asset.status == Asset.STATUS_ACTIVE)
    maintenance_count = sum(1 for asset in assets if asset.status == Asset.STATUS_IN_MAINTENANCE)
    total_value = sum((_asset_value(asset) for asset in assets), Decimal("0"))

    return {
        "subject_user": subject_user,
        "assets": assets,
        "transfers": list(transfers_qs[:50]),
        "maintenance_records": list(maintenance_qs[:50]),
        "activities": list(activities_qs[:50]),
        "summary": {
            "total_assets": len(assets),
            "active_assets": active_count,
            "maintenance_assets": maintenance_count,
            "other_assets": max(len(assets) - active_count - maintenance_count, 0),
            "total_value": total_value,
        },
    }


def render_individual_assets_dataframe(report_data: Dict[str, object]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for asset in report_data["assets"]:
        rows.append(
            {
                "Person": _display_user(report_data["subject_user"]),
                "Asset": _asset_display_name(asset),
                "Category": asset.category.name,
                "Asset Tag": asset.asset_tag or "",
                "Serial Number": asset.serial_number or "",
                "Status": asset.get_status_display(),
                "Branch": asset.branch.name if asset.branch else "Head Office",
                "Value": str(_asset_value(asset)),
                "Created": asset.created_at.strftime("%Y-%m-%d %H:%M"),
                "Updated": asset.updated_at.strftime("%Y-%m-%d %H:%M"),
            }
        )
    return pd.DataFrame(rows)


def build_individual_excel_bytes(report_data: Dict[str, object]) -> bytes:
    buffer = io.BytesIO()
    subject = report_data["subject_user"]
    summary = report_data["summary"]

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {"Metric": "Person", "Value": _display_user(subject)},
                {"Metric": "Username", "Value": subject.username},
                {"Metric": "Email", "Value": subject.email or ""},
                {"Metric": "Role", "Value": subject.get_role_display()},
                {"Metric": "Total Assets", "Value": summary["total_assets"]},
                {"Metric": "Active Assets", "Value": summary["active_assets"]},
                {"Metric": "In Maintenance", "Value": summary["maintenance_assets"]},
                {"Metric": "Total Value", "Value": str(summary["total_value"])},
            ]
        ).to_excel(writer, index=False, sheet_name="Summary")

        render_individual_assets_dataframe(report_data).to_excel(writer, index=False, sheet_name="Assets")

        pd.DataFrame(
            [
                {
                    "Asset": _asset_display_name(t.asset),
                    "From": _display_user(t.from_user),
                    "To": _display_user(t.to_user),
                    "State": t.get_state_display(),
                    "Initiator": _display_user(t.initiator),
                    "Approved By": _display_user(t.approved_by),
                    "Created": t.created_at.strftime("%Y-%m-%d %H:%M"),
                }
                for t in report_data["transfers"]
            ]
        ).to_excel(writer, index=False, sheet_name="Transfers")

        pd.DataFrame(
            [
                {
                    "Asset": _asset_display_name(record.asset),
                    "Status": record.get_status_display(),
                    "Scheduled For": record.scheduled_for.strftime("%Y-%m-%d"),
                    "Performed By": _display_user(record.performed_by),
                    "Cost": str(record.cost or ""),
                    "Description": record.description,
                }
                for record in report_data["maintenance_records"]
            ]
        ).to_excel(writer, index=False, sheet_name="Maintenance")

        pd.DataFrame(
            [
                {
                    "Action": activity.get_action_display(),
                    "Asset": _asset_display_name(activity.asset) if activity.asset else "",
                    "Branch": activity.branch.name if activity.branch else "",
                    "Details": activity.details,
                    "Timestamp": activity.timestamp.strftime("%Y-%m-%d %H:%M"),
                }
                for activity in report_data["activities"]
            ]
        ).to_excel(writer, index=False, sheet_name="Activity")

    return buffer.getvalue()


def build_individual_pdf_bytes(report_data: Dict[str, object], metadata: Dict[str, object]) -> bytes:
    context = {
        "report_data": report_data,
        "metadata": metadata,
        "generated_date": timezone.now(),
    }
    html_string = render_to_string("reports/individual_report_pdf.html", context)
    buffer = io.BytesIO()
    HTML(string=html_string, base_url=metadata.get("base_url")).write_pdf(buffer)
    return buffer.getvalue()
