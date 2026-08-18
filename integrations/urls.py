from django.urls import path

from . import views


app_name = 'integrations'

urlpatterns = [
    path('customers/', views.SyncedCustomerListView.as_view(), name='synced_customer_list'),
    path('customers/<uuid:external_uuid>/', views.SyncedCustomerDetailView.as_view(), name='synced_customer_detail'),
    path('api/customer-sync-config/', views.customer_sync_config, name='customer_sync_config'),
    path('api/customer-sync-config/update/', views.customer_sync_config_update, name='customer_sync_config_update'),
    path('api/customer-sync/run/', views.run_customer_sync, name='run_customer_sync'),
]
