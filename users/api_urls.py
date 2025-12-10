from django.urls import path
from . import api_views
from . import api_retirement

urlpatterns = [
    path('users/', api_views.api_users_list, name='api_users_list'),
    path('users/create/', api_views.api_user_create, name='api_user_create'),
    path('users/update-role/', api_views.api_user_update_role, name='api_user_update_role'),
    path('users/my-permissions/', api_views.api_current_user_permissions, name='api_current_user_permissions'),
    path('users/<int:user_id>/', api_views.api_user_details, name='api_user_details'),
    path('users/<int:user_id>/update/', api_views.api_user_update, name='api_user_update'),
    path('users/<int:user_id>/delete/', api_views.api_user_delete, name='api_user_delete'),
    path('roles/permissions/', api_views.api_roles_permissions, name='api_roles_permissions'),
    path('test-role-update/', api_views.api_test_role_update, name='api_test_role_update'),
    path('csrf-token/', api_views.api_csrf_token, name='api_csrf_token'),
    
    # ========================================================================
    # WORLD-CLASS: Self-Service Retirement API Endpoints (NEW)
    # ========================================================================
    
    # User Self-Service Endpoints
    path('retirement/request/', api_retirement.api_retirement_submit_request, name='api_retirement_submit'),
    path('retirement/my-request/', api_retirement.api_retirement_my_request, name='api_retirement_my_request'),
    path('retirement/my-request/cancel/', api_retirement.api_retirement_cancel_my_request, name='api_retirement_cancel_mine'),
    
    # Manager/Admin Approval Endpoints
    path('retirement/pending-approvals/', api_retirement.api_retirement_pending_approvals, name='api_retirement_pending'),
    path('retirement/<uuid:retirement_id>/approve/', api_retirement.api_retirement_approve, name='api_retirement_approve'),
    path('retirement/<uuid:retirement_id>/reject/', api_retirement.api_retirement_reject, name='api_retirement_reject'),
    
    # Admin Processing Endpoints
    path('retirement/approved-requests/', api_retirement.api_retirement_approved_list, name='api_retirement_approved_list'),
    path('retirement/<uuid:retirement_id>/start/', api_retirement.api_retirement_start_processing, name='api_retirement_start'),
    
    # Dashboard & Reporting Endpoints
    path('retirement/dashboard/', api_retirement.api_retirement_dashboard_stats, name='api_retirement_dashboard'),
    path('retirement/<uuid:retirement_id>/timeline/', api_retirement.api_retirement_timeline, name='api_retirement_timeline'),
]