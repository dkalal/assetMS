"""
URL configuration for assetms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from assets.views import (
    asset_create, get_dynamic_fields, AssetListView, AssetDetailView, AssetScanView, asset_by_code, AssetDetailByUUIDView, asset_export, AssetBulkImportView, download_import_template, dashboard_summary_api, dashboard_activity_api, dashboard_chart_data_api,
    recent_added_assets_api, recent_scans_api, recent_transfers_api, recent_maintenance_api, full_audit_log_api, user_assets_api, user_activity_api, api_create_category, api_categories, api_category_fields, api_create_field, api_update_field, api_delete_field
)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView, RedirectView
from reports.views import reports_dashboard, generate_report
from audit.views import audit_dashboard
from users.views import profile
from assets.views import AssetUpdateView, DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
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
    path('', include(('users.urls', 'users'), namespace='users')),
    path('assets/export/', asset_export, name='asset_export'),
    path('test-modal/', TemplateView.as_view(template_name='test_modal.html'), name='test_modal'),
    path('assets/bulk-import/', AssetBulkImportView.as_view(), name='asset_bulk_import'),
    path('assets/download-import-template/', download_import_template, name='download_import_template'),
    path('reports/', reports_dashboard, name='reports_dashboard'),
    path('reports/generate/', generate_report, name='generate_report'),
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
    path('api/create-category/', api_create_category, name='api_create_category'),
    path('api/categories/', api_categories, name='api_categories'),
    # --- Dynamic Field Management API ---
    path('api/category/<int:category_id>/fields/', api_category_fields, name='api_category_fields'),
    path('api/category/<int:category_id>/fields/create/', api_create_field, name='api_create_field'),
    path('api/field/<int:field_id>/update/', api_update_field, name='api_update_field'),
    path('api/field/<int:field_id>/delete/', api_delete_field, name='api_delete_field'),
    path('api/', include('users.api_urls')),
    
    # Help and Documents
    path('help/', __import__('help.views', fromlist=['HelpCenterView']).HelpCenterView.as_view(), name='help_center'),
    path('documents/', __import__('help.views', fromlist=['DocumentsView']).DocumentsView.as_view(), name='documents'),
    
    # Legacy/alias routes
    path('security/privacy', RedirectView.as_view(pattern_name='settings:security_privacy_settings', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
