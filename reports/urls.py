"""
URL Configuration for Reports Module
"""

from django.urls import path
from . import views, preview_views

app_name = 'reports'

urlpatterns = [
    # Main dashboard
    path('', views.reports_dashboard, name='reports_dashboard'),
    
    # Report generation
    path('generate/', views.generate_report, name='generate_report'),
    path('individual/<int:user_id>/export/', views.export_individual_report, name='export_individual_report'),
    
    # Reports analytics APIs
    path('api/trend/', views.api_report_trend, name='api_report_trend'),
    path('api/types/', views.api_report_types, name='api_report_types'),
    
    # Preview API endpoints
    path('api/preview-export/', preview_views.api_preview_export, name='api_preview_export'),
]
