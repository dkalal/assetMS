from django.urls import path

from . import api_views, views, asset_creation_views
from .views import AssetUpdateView, asset_delete, asset_bulk_delete, regenerate_qr_code, bulk_regenerate_qr_codes
from .asset_creation_views import AssetCreationRequestView, api_pending_asset_creation_requests, api_quick_approve_asset_creation

urlpatterns = [
    path('<uuid:uuid>/edit/', AssetUpdateView.as_view(), name='asset_update'),
    path('<int:asset_id>/delete/', asset_delete, name='asset_delete'),
    path('bulk-delete/', asset_bulk_delete, name='asset_bulk_delete'),
    path('<uuid:uuid>/regenerate-qr/', regenerate_qr_code, name='regenerate_qr_code'),
    path('bulk-regenerate-qr/', bulk_regenerate_qr_codes, name='bulk_regenerate_qr_codes'),
    # Asset Creation Requests (Manager Workflow)
    path('request-creation/', AssetCreationRequestView.as_view(), name='asset_creation_request'),
    path('api/pending-creation-requests/', api_pending_asset_creation_requests, name='api_pending_asset_creation_requests'),
    path('api/quick-approve-creation/<int:request_id>/', api_quick_approve_asset_creation, name='api_quick_approve_asset_creation'),
    # User Filtering API
    path('api/users-by-branch/', views.api_users_by_branch, name='api_users_by_branch'),
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
    # Phase 1: World-Class Asset Registration Features
    path('api/check-duplicate-assets/', api_views.api_check_duplicate_assets, name='api_check_duplicate_assets'),
    path('api/smart-suggestions/', api_views.api_smart_suggestions, name='api_smart_suggestions'),
    # Category Management
    path('api/category/<int:category_id>/update/', api_views.api_category_update, name='api_category_update'),
    path('api/category/<int:category_id>/delete/', api_views.api_category_delete, name='api_category_delete'),
]