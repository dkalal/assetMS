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
    
    # Preview API endpoints
    path('api/preview-export/', preview_views.api_preview_export, name='api_preview_export'),
]
