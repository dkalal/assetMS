"""
WORLD-CLASS Export Preview Service
====================================

Unified preview service for ALL export types (assets, reports, maintenance, etc.)
Inspired by ServiceNow ITAM, IBM Maximo, SAP EAM, and our own import preview.

Features:
- Preview first 100 rows for quick feedback
- Real-time validation and error detection
- Statistics and data quality metrics
- Column analysis (types, nulls, uniqueness)
- Estimated file size and export duration
- Format-specific preview (Excel, CSV, PDF)
- Multi-tenancy and security enforced

Author: AssetMS Development Team
Date: November 2025
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date

import pandas as pd
from django.core.cache import cache
from django.utils import timezone

from assets.models import Asset
from .services import ReportFilters, fetch_assets_cached, render_assets_dataframe


@dataclass
class PreviewMetrics:
    """Data quality and preview metrics"""
    total_rows: int
    preview_rows: int
    total_columns: int
    has_more: bool
    estimated_file_size_kb: int
    estimated_export_time_seconds: float
    data_quality_score: float  # 0-100
    warnings: List[str]
    errors: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ColumnMetadata:
    """Metadata about a column"""
    name: str
    display_name: str
    data_type: str  # string, number, date, boolean
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: List[str]
    has_nulls: bool
    is_unique: bool
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PreviewResult:
    """Complete preview result with data, metrics, and metadata"""
    success: bool
    preview_data: List[Dict[str, Any]]
    columns: List[str]
    column_metadata: List[ColumnMetadata]
    metrics: PreviewMetrics
    filters_applied: Dict[str, Any]
    export_format: str
    report_type: str
    company_name: str
    branch_name: Optional[str]
    generated_at: str
    cache_key: str
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict"""
        return {
            'success': self.success,
            'preview_data': self.preview_data,
            'columns': self.columns,
            'column_metadata': [col.to_dict() for col in self.column_metadata],
            'metrics': self.metrics.to_dict(),
            'filters_applied': self.filters_applied,
            'export_format': self.export_format,
            'report_type': self.report_type,
            'company_name': self.company_name,
            'branch_name': self.branch_name,
            'generated_at': self.generated_at,
            'cache_key': self.cache_key,
        }


class ExportPreviewService:
    """
    Unified service for generating export previews
    
    Usage:
        service = ExportPreviewService()
        result = service.generate_preview(
            company=company,
            report_type='asset_summary',
            export_format='xlsx',
            filters=filters,
            branch=branch,
            preview_limit=100
        )
    """
    
    # Preview limits
    MAX_PREVIEW_ROWS = 100
    DEFAULT_PREVIEW_ROWS = 50
    CACHE_TTL = 300  # 5 minutes
    
    # File size estimation (KB per row)
    SIZE_ESTIMATE = {
        'csv': 0.5,
        'excel': 1.0,
        'xlsx': 1.0,
        'pdf': 2.0,
    }
    
    # Export time estimation (seconds per 1000 rows)
    TIME_ESTIMATE = {
        'csv': 1.0,
        'excel': 2.0,
        'xlsx': 2.0,
        'pdf': 5.0,
    }
    
    def __init__(self):
        self.warnings = []
        self.errors = []
    
    def generate_preview(
        self,
        company,
        report_type: str,
        export_format: str,
        filters: ReportFilters,
        branch=None,
        preview_limit: int = DEFAULT_PREVIEW_ROWS,
        user=None
    ) -> PreviewResult:
        """
        Generate preview for any report type
        
        Args:
            company: Company instance
            report_type: Type of report (asset_summary, maintenance, custom)
            export_format: Format (csv, excel, xlsx, pdf)
            filters: Report filters
            branch: Optional branch filter
            preview_limit: Number of rows to preview (max 100)
            user: User requesting preview (for audit)
        
        Returns:
            PreviewResult with data, metrics, and metadata
        """
        self.warnings = []
        self.errors = []
        
        # Validate inputs
        preview_limit = min(preview_limit, self.MAX_PREVIEW_ROWS)
        export_format = export_format.lower()
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            company, report_type, export_format, filters, branch
        )
        
        # Check cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return PreviewResult(**cached_result)
        
        # Generate preview based on report type
        try:
            if report_type == 'asset_summary':
                result = self._preview_asset_summary(
                    company, branch, filters, export_format, preview_limit, user
                )
            elif report_type == 'maintenance':
                result = self._preview_maintenance(
                    company, branch, filters, export_format, preview_limit, user
                )
            elif report_type == 'custom':
                result = self._preview_custom(
                    company, branch, filters, export_format, preview_limit, user
                )
            else:
                raise ValueError(f'Unsupported report type: {report_type}')
            
            # Cache the result
            cache.set(cache_key, result.to_dict(), self.CACHE_TTL)
            
            return result
            
        except Exception as e:
            self.errors.append(str(e))
            return self._create_error_result(
                company, report_type, export_format, filters, branch, str(e)
            )
    
    def _preview_asset_summary(
        self,
        company,
        branch,
        filters: ReportFilters,
        export_format: str,
        preview_limit: int,
        user
    ) -> PreviewResult:
        """Generate preview for asset summary report"""
        # Fetch assets (use cached version for performance)
        assets = fetch_assets_cached(company, branch, filters, ttl=self.CACHE_TTL)
        
        if not assets:
            self.warnings.append('No assets found matching the selected filters.')
            return self._create_empty_result(
                company, 'asset_summary', export_format, filters, branch
            )
        
        # Convert to DataFrame for analysis
        df = render_assets_dataframe(assets)
        
        # Generate preview
        return self._create_preview_result(
            df, company, 'asset_summary', export_format, filters, branch, preview_limit
        )
    
    def _preview_maintenance(
        self,
        company,
        branch,
        filters: ReportFilters,
        export_format: str,
        preview_limit: int,
        user
    ) -> PreviewResult:
        """Generate preview for maintenance report"""
        from assets.models import MaintenanceRecord
        
        # Build queryset
        records = MaintenanceRecord.objects.filter(
            company=company
        ).select_related('asset', 'asset__category', 'asset__branch', 'performed_by')
        
        # Apply filters
        if branch:
            records = records.filter(asset__branch=branch)
        if filters.status:
            records = records.filter(status=filters.status)
        if filters.date_from:
            records = records.filter(scheduled_date__gte=filters.date_from)
        if filters.date_to:
            records = records.filter(scheduled_date__lte=filters.date_to)
        
        records = list(records[:10000])  # Limit for performance
        
        if not records:
            self.warnings.append('No maintenance records found matching the selected filters.')
            return self._create_empty_result(
                company, 'maintenance', export_format, filters, branch
            )
        
        # Convert to DataFrame
        data = []
        for record in records:
            data.append({
                'Asset': record.asset.dynamic_data.get('name', f'Asset #{record.asset.pk}'),
                'Category': record.asset.category.name,
                'Branch': record.asset.branch.name if record.asset.branch else 'N/A',
                'Type': record.get_maintenance_type_display(),
                'Status': record.get_status_display(),
                'Scheduled Date': record.scheduled_date.strftime('%Y-%m-%d') if record.scheduled_date else 'N/A',
                'Started At': record.started_at.strftime('%Y-%m-%d %H:%M') if record.started_at else 'Not Started',
                'Completed At': record.completed_at.strftime('%Y-%m-%d %H:%M') if record.completed_at else 'Not Completed',
                'Performed By': record.performed_by.get_full_name() if record.performed_by else 'N/A',
                'Cost': f'{record.cost:.2f}' if record.cost else '0.00',
                'Notes': record.notes[:50] if record.notes else '',
            })
        
        df = pd.DataFrame(data)
        
        return self._create_preview_result(
            df, company, 'maintenance', export_format, filters, branch, preview_limit
        )
    
    
    def _preview_custom(
        self,
        company,
        branch,
        filters: ReportFilters,
        export_format: str,
        preview_limit: int,
        user
    ) -> PreviewResult:
        """Generate preview for custom report (comprehensive asset data)"""
        # Use asset summary as base for custom reports
        return self._preview_asset_summary(
            company, branch, filters, export_format, preview_limit, user
        )
    
    def _create_preview_result(
        self,
        df: pd.DataFrame,
        company,
        report_type: str,
        export_format: str,
        filters: ReportFilters,
        branch,
        preview_limit: int
    ) -> PreviewResult:
        """Create PreviewResult from DataFrame"""
        total_rows = len(df)
        preview_rows = min(total_rows, preview_limit)
        has_more = total_rows > preview_limit
        
        # Get preview data
        preview_df = df.head(preview_limit)
        preview_data = preview_df.to_dict('records')
        
        # Serialize values (handle Decimal, dates, etc.)
        preview_data = self._serialize_preview_data(preview_data)
        
        # Analyze columns
        columns = list(df.columns)
        column_metadata = self._analyze_columns(df)
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            df, total_rows, preview_rows, has_more, export_format
        )
        
        # Build filters applied summary
        filters_applied = self._build_filters_summary(filters, branch)
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            company, report_type, export_format, filters, branch
        )
        
        return PreviewResult(
            success=True,
            preview_data=preview_data,
            columns=columns,
            column_metadata=column_metadata,
            metrics=metrics,
            filters_applied=filters_applied,
            export_format=export_format,
            report_type=report_type,
            company_name=company.name,
            branch_name=branch.name if branch else None,
            generated_at=timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            cache_key=cache_key
        )
    
    def _analyze_columns(self, df: pd.DataFrame) -> List[ColumnMetadata]:
        """Analyze DataFrame columns and generate metadata"""
        column_metadata = []
        
        for col in df.columns:
            series = df[col]
            null_count = series.isnull().sum()
            null_percentage = (null_count / len(series) * 100) if len(series) > 0 else 0
            unique_count = series.nunique()
            
            # Get sample values (non-null, unique, first 5)
            sample_values = [
                str(val) for val in series.dropna().unique()[:5]
            ]
            
            # Determine data type
            if pd.api.types.is_numeric_dtype(series):
                data_type = 'number'
            elif pd.api.types.is_datetime64_any_dtype(series):
                data_type = 'date'
            elif pd.api.types.is_bool_dtype(series):
                data_type = 'boolean'
            else:
                data_type = 'string'
            
            column_metadata.append(ColumnMetadata(
                name=col,
                display_name=col.replace('_', ' ').title(),
                data_type=data_type,
                null_count=int(null_count),
                null_percentage=round(null_percentage, 1),
                unique_count=int(unique_count),
                sample_values=sample_values,
                has_nulls=null_count > 0,
                is_unique=unique_count == len(series)
            ))
        
        return column_metadata
    
    def _calculate_metrics(
        self,
        df: pd.DataFrame,
        total_rows: int,
        preview_rows: int,
        has_more: bool,
        export_format: str
    ) -> PreviewMetrics:
        """Calculate preview metrics"""
        # Estimate file size
        size_per_row = self.SIZE_ESTIMATE.get(export_format, 1.0)
        estimated_size_kb = int(total_rows * size_per_row)
        
        # Estimate export time
        time_per_1k_rows = self.TIME_ESTIMATE.get(export_format, 2.0)
        estimated_time = (total_rows / 1000) * time_per_1k_rows
        
        # Calculate data quality score
        data_quality_score = self._calculate_data_quality_score(df)
        
        # Add warnings based on analysis
        if total_rows > 10000:
            self.warnings.append(f'Large export ({total_rows:,} rows). Consider adding filters to reduce size.')
        
        if estimated_size_kb > 50000:  # > 50 MB
            self.warnings.append(f'Estimated file size is large (~{estimated_size_kb//1024} MB). Export may take several minutes.')
        
        if data_quality_score < 70:
            self.warnings.append(f'Data quality score is low ({data_quality_score:.0f}/100). Review missing values.')
        
        return PreviewMetrics(
            total_rows=total_rows,
            preview_rows=preview_rows,
            total_columns=len(df.columns),
            has_more=has_more,
            estimated_file_size_kb=estimated_size_kb,
            estimated_export_time_seconds=round(estimated_time, 1),
            data_quality_score=round(data_quality_score, 1),
            warnings=self.warnings,
            errors=self.errors
        )
    
    def _calculate_data_quality_score(self, df: pd.DataFrame) -> float:
        """
        Calculate data quality score (0-100)
        Based on: completeness, uniqueness, consistency
        """
        if len(df) == 0:
            return 0.0
        
        # Completeness: % of non-null values
        total_cells = df.size
        non_null_cells = df.count().sum()
        completeness_score = (non_null_cells / total_cells * 100) if total_cells > 0 else 0
        
        # Uniqueness: Average uniqueness ratio per column
        uniqueness_scores = []
        for col in df.columns:
            unique_ratio = df[col].nunique() / len(df) * 100
            uniqueness_scores.append(unique_ratio)
        uniqueness_score = sum(uniqueness_scores) / len(uniqueness_scores) if uniqueness_scores else 0
        
        # Weighted average (completeness is more important)
        quality_score = (completeness_score * 0.7) + (uniqueness_score * 0.3)
        
        return quality_score
    
    def _serialize_preview_data(self, data: List[Dict]) -> List[Dict]:
        """Serialize data for JSON response (handle Decimal, dates, etc.)"""
        serialized = []
        for row in data:
            serialized_row = {}
            for key, value in row.items():
                if isinstance(value, Decimal):
                    serialized_row[key] = float(value)
                elif isinstance(value, (datetime, date)):
                    serialized_row[key] = value.strftime('%Y-%m-%d %H:%M:%S') if isinstance(value, datetime) else value.strftime('%Y-%m-%d')
                elif pd.isna(value):
                    serialized_row[key] = None
                else:
                    serialized_row[key] = str(value) if value is not None else None
            serialized.append(serialized_row)
        return serialized
    
    def _build_filters_summary(self, filters: ReportFilters, branch) -> Dict[str, Any]:
        """Build human-readable summary of applied filters"""
        summary = {}
        
        if filters.status:
            summary['Status'] = filters.status.replace('_', ' ').title()
        if branch:
            summary['Branch'] = branch.name
        if filters.date_from:
            summary['Date From'] = filters.date_from
        if filters.date_to:
            summary['Date To'] = filters.date_to
        
        return summary
    
    def _generate_cache_key(
        self,
        company,
        report_type: str,
        export_format: str,
        filters: ReportFilters,
        branch
    ) -> str:
        """Generate unique cache key for preview"""
        key_parts = [
            'export_preview',
            str(company.id),
            report_type,
            export_format,
            filters.cache_key_suffix(),
            str(branch.id) if branch else 'all'
        ]
        key_string = ':'.join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]
    
    def _create_empty_result(
        self,
        company,
        report_type: str,
        export_format: str,
        filters: ReportFilters,
        branch
    ) -> PreviewResult:
        """Create empty preview result"""
        return PreviewResult(
            success=True,
            preview_data=[],
            columns=[],
            column_metadata=[],
            metrics=PreviewMetrics(
                total_rows=0,
                preview_rows=0,
                total_columns=0,
                has_more=False,
                estimated_file_size_kb=0,
                estimated_export_time_seconds=0,
                data_quality_score=0,
                warnings=self.warnings,
                errors=self.errors
            ),
            filters_applied=self._build_filters_summary(filters, branch),
            export_format=export_format,
            report_type=report_type,
            company_name=company.name,
            branch_name=branch.name if branch else None,
            generated_at=timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            cache_key=self._generate_cache_key(company, report_type, export_format, filters, branch)
        )
    
    def _create_error_result(
        self,
        company,
        report_type: str,
        export_format: str,
        filters: ReportFilters,
        branch,
        error_message: str
    ) -> PreviewResult:
        """Create error preview result"""
        self.errors.append(error_message)
        result = self._create_empty_result(company, report_type, export_format, filters, branch)
        result.success = False
        return result
