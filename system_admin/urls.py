"""
System Admin URLs
=================
Purpose: URL patterns for system admin views
"""

from django.urls import path
from . import views

app_name = 'system_admin'

urlpatterns = [
    path('system/', views.system_dashboard_view, name='dashboard'),
    path('system/companies/', views.company_list_view, name='company_list'),
    path('system/companies/create/', views.create_company_view, name='create_company'),
    path('system/companies/<int:pk>/', views.company_detail_view, name='company_detail'),
    path('system/companies/<int:pk>/suspend/', views.suspend_company_view, name='suspend_company'),
    path('system/companies/<int:pk>/reactivate/', views.reactivate_company_view, name='reactivate_company'),
    path('system/impersonate/<int:user_id>/', views.impersonate_user_view, name='impersonate'),
    path('system/exit-impersonation/', views.exit_impersonation_view, name='exit_impersonation'),
]







