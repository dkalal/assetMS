from django.urls import path

from . import maintenance_views

app_name = "maintenance"

urlpatterns = [
    path("", maintenance_views.MaintenanceListView.as_view(), name="list"),
    path("schedule/<uuid:asset_uuid>/", maintenance_views.MaintenanceScheduleView.as_view(), name="schedule"),
    path("start/<int:pk>/", maintenance_views.MaintenanceStartView.as_view(), name="start"),
    path("complete/<int:pk>/", maintenance_views.MaintenanceCompletionView.as_view(), name="complete"),
    path("cancel/<int:pk>/", maintenance_views.MaintenanceCancellationView.as_view(), name="cancel"),
    path("api/seed-data/", maintenance_views.seed_maintenance_data, name="seed_data"),
]
