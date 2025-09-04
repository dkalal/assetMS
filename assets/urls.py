from django.urls import path
from .views import AssetUpdateView, asset_delete, asset_bulk_delete

urlpatterns = [
    path('<uuid:uuid>/edit/', AssetUpdateView.as_view(), name='asset_update'),
    path('<int:asset_id>/delete/', asset_delete, name='asset_delete'),
    path('bulk-delete/', asset_bulk_delete, name='asset_bulk_delete'),
]