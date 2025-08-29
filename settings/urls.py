from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    # Main settings dashboard
    path('', views.settings_dashboard, name='settings_dashboard'),
    
    # User management
    path('users/', views.user_management, name='user_management'),
    path('session-management/', views.session_management, name='session_management'),
    
    # Organization settings
    path('organization/', views.organization_settings, name='organization_settings'),
    
    # Security & Privacy settings
    path('security/', views.security_privacy_settings, name='security_privacy_settings'),
    
    # API endpoints
    path('api/users/', views.api_users_management, name='api_users_management'),
    path('api/invite-user/', views.api_invite_user, name='api_invite_user'),
    path('api/session-stats/', views.api_session_stats, name='api_session_stats'),
    path('api/access-logs/', views.api_access_logs, name='api_access_logs'),
    path('api/session-details/', views.api_session_details, name='api_session_details'),
    path('api/session/heartbeat/', views.api_session_heartbeat, name='api_session_heartbeat'),
    path('api/toggle-user-status/', views.api_toggle_user_status, name='api_toggle_user_status'),
    path('api/update-user/', views.api_update_user, name='api_update_user'),
    path('api/update/', views.update_setting, name='update_setting'),
    path('api/create/', views.create_setting, name='create_setting'),
    
    # Session management endpoints
    path('api/terminate-session/', views.api_terminate_session, name='api_terminate_session'),
    path('api/terminate-user-sessions/', views.api_terminate_user_sessions, name='api_terminate_user_sessions'),
    path('api/user-session-history/', views.api_user_session_history, name='api_user_session_history'),
    path('api/session-report/', views.api_session_report, name='api_session_report'),
    path('api/cleanup-sessions/', views.api_cleanup_sessions, name='api_cleanup_sessions'),
    
    # Organization API endpoints
    path('api/organization/', views.api_organization_profile, name='api_organization_profile'),
    path('api/organization/update/', views.api_update_organization, name='api_update_organization'),
    
    # Security API endpoints
    path('api/security/', views.api_security_settings, name='api_security_settings'),
    path('api/security/metrics/', views.api_security_metrics, name='api_security_metrics'),
    path('api/security/update/', views.api_update_security_settings, name='api_update_security_settings'),
    path('api/security/activities/', views.api_security_activities, name='api_security_activities'),
]
