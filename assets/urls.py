from django.urls import path
from .views import AssetUpdateView

urlpatterns = [
    path('assets/<uuid:uuid>/edit/', AssetUpdateView.as_view(), name='asset_update'),
] 