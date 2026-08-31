from django.urls import path
from django.views.generic import RedirectView

from . import api_views, views, asset_creation_views, asset_disposal_views, bulk_import_views
from reports import preview_views
from .views import AssetUpdateView, asset_delete, asset_bulk_delete, regenerate_qr_code, bulk_regenerate_qr_codes
from .asset_creation_views import AssetCreationRequestView, api_pending_asset_creation_requests, api_quick_approve_asset_creation
from .asset_disposal_views import AssetDisposalRequestView, api_pending_disposal_requests

# WORLD-CLASS: App namespace for URL routing
app_name = 'assets'

urlpatterns = [
    # DEBUG ENDPOINT - Remove in production
    
    # Asset List View
    path('', views.AssetListView.as_view(), name='list'),
    
    # Historical bookmarks now enter the canonical permission-aware workflow.
    path(
        'register/wizard/',
        RedirectView.as_view(pattern_name='asset_register', permanent=False),
        name='asset_register_wizard',
    ),
    
    path('<uuid:uuid>/edit/', AssetUpdateView.as_view(), name='asset_update'),
    path('<int:asset_id>/delete/', asset_delete, name='asset_delete'),  # DEPRECATED - redirects to disposal
    path('bulk-delete/', asset_bulk_delete, name='asset_bulk_delete'),  # DEPRECATED
    path('admin/permanent-delete/<int:asset_id>/', views.asset_permanent_delete, name='asset_permanent_delete'),  # Super admin only
    path('<uuid:uuid>/regenerate-qr/', regenerate_qr_code, name='regenerate_qr_code'),
    path('bulk-regenerate-qr/', bulk_regenerate_qr_codes, name='bulk_regenerate_qr_codes'),
    # Asset Creation Requests (Manager Workflow)
    path('request-creation/', AssetCreationRequestView.as_view(), name='asset_creation_request'),
    path('api/pending-creation-requests/', api_pending_asset_creation_requests, name='api_pending_asset_creation_requests'),
    path('api/quick-approve-creation/<int:request_id>/', api_quick_approve_asset_creation, name='api_quick_approve_asset_creation'),
    # Asset Disposal Requests (Approval Workflow)
    path('<uuid:asset_uuid>/request-disposal/', AssetDisposalRequestView.as_view(), name='asset_disposal_request'),
    path('api/pending-disposal-requests/', api_pending_disposal_requests, name='api_pending_disposal_requests'),
    # User Filtering API (Branch-based cascading selection)
    path('api/users-by-branch/', api_views.api_users_by_branch, name='api_users_by_branch'),
    # WORLD-CLASS: Assets List API endpoint
    path('api/list/', api_views.api_asset_list, name='api_asset_list'),
    # Transfer Management
    path('transfers/', views.transfer_dashboard, name='transfer_dashboard'),
    path('transfers/', views.transfer_dashboard, name='asset_transfers'),
    path('api/transfers/list/', api_views.api_transfer_list, name='asset_transfer_list'),
    path('api/transfers/initiate/', api_views.api_transfer_initiate, name='asset_transfer_initiate'),
    path('api/transfers/cancel/', api_views.api_transfer_cancel, name='asset_transfer_cancel'),
    path('api/transfers/receiver-decision/', api_views.api_transfer_receiver_decision, name='asset_transfer_receiver_decision'),
    path('api/transfers/admin-review/', api_views.api_transfer_admin_review, name='asset_transfer_admin_review'),
    path('api/transfers/alerts/', api_views.api_transfer_alerts, name='asset_transfer_alerts'),
    path('api/category-fields-enhanced/', api_views.api_category_fields_enhanced, name='api_category_fields_enhanced'),
    path('api/check-unique-field/', api_views.api_check_unique_field, name='api_check_unique_field'),
    # WORLD-CLASS DUPLICATE DETECTION SYSTEM
    path('api/check-duplicates/', api_views.api_check_duplicates, name='api_check_duplicates'),
    path('api/validate-bulk-duplicates/', api_views.api_validate_bulk_duplicates, name='api_validate_bulk_duplicates'),
    # Category Management
    path('api/category/<int:category_id>/update/', api_views.api_category_update, name='api_category_update'),
    path('api/category/<int:category_id>/delete/', api_views.api_category_delete, name='api_category_delete'),
    # Dynamic Data Refresh (Real-time updates)
    path('api/asset/<uuid:uuid>/refresh/', api_views.api_asset_data_refresh, name='api_asset_data_refresh'),
    # Quick Edit API (Inline editing)
    path('api/<uuid:uuid>/quick-edit/', api_views.api_asset_quick_edit, name='api_asset_quick_edit'),
    
    # ========================================
    # Export Preview Feature
    # World-class unified export preview (ServiceNow/IBM Maximo style)
    # ========================================
    path('api/export-preview/', preview_views.api_preview_asset_export, name='asset_export_preview'),
    
    # ========================================
    # Bulk Import Feature (Phase 8)
    # World-class CSV/Excel import (Salesforce/ServiceNow style)
    # ========================================
    path('bulk-import/', bulk_import_views.bulk_import_view, name='bulk_import'),
    path('api/bulk-import-template/', bulk_import_views.download_import_template, name='bulk_import_template'),
    path('api/validate-bulk-data/', bulk_import_views.validate_bulk_data, name='validate_bulk_data'),
    path('api/bulk-import/', bulk_import_views.execute_bulk_import, name='execute_bulk_import'),
    # Asset maintenance request (user self-service)
    path('api/asset/<uuid:uuid>/request-maintenance/', api_views.api_request_maintenance, name='asset_request_maintenance'),
]
