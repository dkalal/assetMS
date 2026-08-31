from django.urls import path

from . import views


app_name = 'integrations'

urlpatterns = [
    # Customer list & 360 detail
    path('customers/', views.SyncedCustomerListView.as_view(), name='synced_customer_list'),
    path('customers/<uuid:external_uuid>/', views.SyncedCustomerDetailView.as_view(), name='synced_customer_detail'),

    # Integration settings (admin)
    path('settings/', views.integration_settings, name='integration_settings'),

    # Notes
    path('api/customers/<uuid:external_uuid>/notes/', views.api_add_customer_note, name='api_add_customer_note'),
    path('api/customer-notes/<int:note_id>/delete/', views.api_delete_customer_note, name='api_delete_customer_note'),

    # Asset link / unlink
    path('api/customers/<uuid:external_uuid>/link-asset/', views.api_link_asset_to_customer, name='api_link_asset'),
    path('api/customers/<uuid:external_uuid>/unlink-asset/', views.api_unlink_asset_from_customer, name='api_unlink_asset'),

    # Customer-to-customer transfer
    path('api/customers/<uuid:external_uuid>/transfer-asset/', views.api_transfer_asset_between_customers, name='api_transfer_asset'),

    # Branch assignment (admin)
    path('api/customers/<uuid:external_uuid>/assign-branch/', views.api_assign_customer_branch, name='api_assign_branch'),

    # Sync config & run (admin)
    path('api/customer-sync-config/', views.customer_sync_config, name='customer_sync_config'),
    path('api/customer-sync-config/update/', views.customer_sync_config_update, name='customer_sync_config_update'),
    path('api/customer-sync/run/', views.run_customer_sync, name='run_customer_sync'),
]
