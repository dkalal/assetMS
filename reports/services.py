from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import pandas as pd
from django.core.cache import cache
from django.template.loader import render_to_string
from weasyprint import HTML

from assets.models import Asset


@dataclass
class ReportFilters:
    status: Optional[str] = None
    branch_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    def cache_key_suffix(self) -> str:
        payload = f"status={self.status}|branch={self.branch_id}|from={self.date_from}|to={self.date_to}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Assets")
    return buffer.getvalue()


def build_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def build_pdf_bytes(assets: Iterable[Asset], metadata: Dict[str, object]) -> bytes:
    html_string = render_to_string("reports/asset_summary_pdf.html", {"assets": assets, "metadata": metadata})
    buffer = io.BytesIO()
    HTML(string=html_string, base_url=metadata.get("base_url")).write_pdf(buffer)
    return buffer.getvalue()
