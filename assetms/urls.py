# URL configuration for the asset management system project.

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from assets.views import (
    AssetBulkImportView,
    AssetDetailByUUIDView,
    AssetDetailView,
    AssetListView,
    AssetScanView,
    AssetUpdateView,
    DashboardView,
    api_categories,
    api_category_analytics,
    api_category_fields,
    api_category_template_detail,
    api_category_templates,
    api_create_category,
    api_create_field,
    api_delete_category,
    api_delete_field,
    api_update_field,
    asset_by_code,
    asset_create,
    asset_export,
    dashboard_activity_api,
    dashboard_chart_data_api,
    dashboard_summary_api,
    download_import_template,
    full_audit_log_api,
    get_dynamic_fields,
    notifications_api,
    recent_added_assets_api,
    recent_maintenance_api,
    recent_scans_api,
    recent_transfers_api,
    user_activity_api,
    user_assets_api,
)
from assets.global_search_views import global_search_api
from assets.api_views import api_category_update as api_category_update_v2
from audit.views import audit_dashboard
from health_check import health_check
from reports.views import generate_report, reports_dashboard, api_report_trend, api_report_types
from reports import preview_views
from tenancy.views import BranchStatusToggleView, TenantSetupWizardView, switch_branch, UserBranchManagementView, BranchManagerManagementView
from tenancy.manager_views import ManagerDashboardView, ManagerPerformanceView
from tenancy.approval_views import ApprovalDashboardView, ApprovalRequestCreateView, ApprovalRequestDetailView, ApprovalActionView


urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/global-search/', global_search_api, name='global_search_api'),
    path('assets/register/', asset_create, name='asset_register'),
    path('api/dynamic-fields/', get_dynamic_fields, name='get_dynamic_fields'),
    path('assets/', AssetListView.as_view(), name='asset_list'),
    path('assets/<int:pk>/', AssetDetailView.as_view(), name='asset_detail'),
    path('scan/', AssetScanView.as_view(), name='asset_scan'),
    path('api/asset-by-code/', asset_by_code, name='asset_by_code'),
    path('assets/<uuid:uuid>/', AssetDetailByUUIDView.as_view(), name='asset_detail_by_uuid'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard_summary_api/', dashboard_summary_api, name='dashboard_summary_api'),
    path('dashboard_activity_api/', dashboard_activity_api, name='dashboard_activity_api'),
    path('dashboard_chart_data_api/', dashboard_chart_data_api, name='dashboard_chart_data_api'),
    path('notifications-api/', notifications_api, name='notifications_api'),
    path('tenancy/switch-branch/', switch_branch, name='switch_branch'),
    path('tenancy/setup/', TenantSetupWizardView.as_view(), name='tenant_setup_wizard'),
    path('tenancy/branches/<int:pk>/toggle/', BranchStatusToggleView.as_view(), name='tenant_branch_toggle'),
    path('tenancy/user-branches/', UserBranchManagementView.as_view(), name='user_branch_management'),
    path('tenancy/branch-managers/', BranchManagerManagementView.as_view(), name='branch_manager_management'),
    path('tenancy/manager-dashboard/', ManagerDashboardView.as_view(), name='manager_dashboard'),
    path('tenancy/manager-performance/', ManagerPerformanceView.as_view(), name='branch_manager_performance'),
    path('tenancy/approvals/', ApprovalDashboardView.as_view(), name='approval_dashboard'),
    path('tenancy/approvals/create/', ApprovalRequestCreateView.as_view(), name='approval_request_create'),
    path('tenancy/approvals/<int:pk>/', ApprovalRequestDetailView.as_view(), name='approval_request_detail'),
    path('tenancy/approvals/<int:pk>/action/', ApprovalActionView.as_view(), name='approval_action'),
    path('maintenance/', include('tenancy.maintenance_urls', namespace='maintenance')),
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False), name='home'),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('assets/export/', asset_export, name='asset_export'),
    path('test-modal/', TemplateView.as_view(template_name='test_modal.html'), name='test_modal'),
    path('assets/bulk-import/', AssetBulkImportView.as_view(), name='asset_bulk_import'),
    path('assets/download-import-template/', download_import_template, name='download_import_template'),
    path('reports/', reports_dashboard, name='reports_dashboard'),
    path('reports/generate/', generate_report, name='generate_report'),
    path('reports/api/trend/', api_report_trend, name='reports_api_trend'),
    path('reports/api/types/', api_report_types, name='reports_api_types'),
    path('reports/api/preview-export/', preview_views.api_preview_export, name='reports_api_preview_export'),
    path('audit/', audit_dashboard, name='audit_dashboard'),
    path('recent-added-assets-api/', recent_added_assets_api, name='recent_added_assets_api'),
    path('recent-scans-api/', recent_scans_api, name='recent_scans_api'),
    path('recent-transfers-api/', recent_transfers_api, name='recent_transfers_api'),
    path('recent-maintenance-api/', recent_maintenance_api, name='recent_maintenance_api'),
    path('full-audit-log-api/', full_audit_log_api, name='full_audit_log_api'),
    path('api/user-assets/', user_assets_api, name='user_assets_api'),
    path('api/user-activity/', user_activity_api, name='user_activity_api'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('settings/', include('settings.urls')),
    path('assets/', include('assets.urls')),
    path('categories/', include('categories.urls')),
    path('accounts/', include('accounts.urls')),
    path('', include('system_admin.urls')),
    path('api/create-category/', api_create_category, name='api_create_category'),
    path('api/categories/', api_categories, name='api_categories'),
    path('api/category-templates/', api_category_templates, name='api_category_templates'),
    path('api/category-template/<str:template_key>/', api_category_template_detail, name='api_category_template_detail'),
    # Alias to match frontend calls
    path('api/category/create/', api_create_category, name='api_create_category_alias'),
    path('api/category/<int:category_id>/delete/', api_delete_category, name='api_delete_category'),
    # Category update endpoint (v2, implemented in assets.api_views)
    path('api/category/<int:category_id>/update/', api_category_update_v2, name='api_category_update'),
    path('api/category/<int:category_id>/analytics/', api_category_analytics, name='api_category_analytics'),
    path('api/category/<int:category_id>/fields/', api_category_fields, name='api_category_fields'),
    path('api/category/<int:category_id>/fields/create/', api_create_field, name='api_create_field'),
    path('api/category/<int:field_id>/update/', api_update_field, name='api_update_field'),
    path('api/field/<int:field_id>/update/', api_update_field, name='api_update_field'),
    path('api/field/<int:field_id>/delete/', api_delete_field, name='api_delete_field'),
    path('api/', include('users.api_urls')),
    path('api/tenancy/branches/', __import__('tenancy.api_views', fromlist=['api_branches_list']).api_branches_list, name='api_branches_list'),
    path('api/tenancy/branches/<int:branch_id>/', __import__('tenancy.api_views', fromlist=['api_branch_detail']).api_branch_detail, name='api_branch_detail'),
    path('api/tenancy/branches/<int:branch_id>/update/', __import__('tenancy.api_views', fromlist=['api_branch_update']).api_branch_update, name='api_branch_update'),
    path('api/tenancy/branches/create/', __import__('tenancy.api_views', fromlist=['api_branch_create']).api_branch_create, name='api_branch_create'),
    path('api/tenancy/branches/<int:branch_id>/delete/', __import__('tenancy.api_views', fromlist=['api_branch_delete']).api_branch_delete, name='api_branch_delete'),
    path('help/', __import__('help.views', fromlist=['HelpCenterView']).HelpCenterView.as_view(), name='help_center'),
    path('documents/', __import__('help.views', fromlist=['DocumentsView']).DocumentsView.as_view(), name='documents'),
    path('security/privacy', RedirectView.as_view(pattern_name='settings:security_privacy_settings', permanent=False)),
]

# Serve media and static files (required for Docker deployment)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
