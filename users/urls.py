from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from . import api_transfer_views
from django.views.decorators.csrf import ensure_csrf_cookie

app_name = 'users'

urlpatterns = [
    # Authentication
    path('login/', views.EnterpriseLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('password/change-required/', views.PasswordChangeRequiredView.as_view(), name='password_change_required'),
    path('accept-invitation/<uuid:token>/', views.accept_invitation, name='accept_invitation'),

    # Password reset (enterprise, multi-tenant)
    path(
        'password-reset/',
        views.EnterprisePasswordResetView.as_view(),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url=reverse_lazy('users:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete',
    ),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('my-retirement/', views.my_retirement_request, name='my_retirement'),
    path('retirement/approvals/', views.retirement_approval_center, name='retirement_approvals'),
    
    # Transfer Requests
    path('my-transfers/', views.my_transfer_requests, name='my_transfer_requests'),
    
    # API Endpoints
    path('api/list/', views.api_user_list, name='api_user_list'),
    
    # Branch Transfer API Endpoints (Admin-Initiated)
    path('api/transfer/initiate/', api_transfer_views.api_initiate_transfer, name='api_initiate_transfer'),
    path('api/transfer/<int:transfer_id>/', api_transfer_views.api_get_transfer, name='api_get_transfer'),
    path('api/transfer/<int:transfer_id>/submit-selections/', api_transfer_views.api_submit_selections, name='api_submit_selections'),
    path('api/transfer/<int:transfer_id>/approve/', api_transfer_views.api_approve_transfer, name='api_approve_transfer'),
    path('api/transfer/<int:transfer_id>/reject/', api_transfer_views.api_reject_transfer, name='api_reject_transfer'),
    path('api/transfer/<int:transfer_id>/cancel/', api_transfer_views.api_cancel_transfer, name='api_cancel_transfer'),
    path('api/transfer/pending/', api_transfer_views.api_get_pending_transfers, name='api_get_pending_transfers'),
    
    # User Self-Service Transfer API Endpoints
    path('api/transfer/user-initiate/', api_transfer_views.user_initiate_transfer, name='user_initiate_transfer'),
    path('api/transfer/<int:transfer_id>/manager-approve/', api_transfer_views.manager_approve_transfer, name='manager_approve_transfer'),
    path('api/transfer/<int:transfer_id>/manager-reject/', api_transfer_views.manager_reject_transfer, name='manager_reject_transfer'),
    path('api/transfer/my-requests/', api_transfer_views.my_transfer_requests, name='my_transfer_requests'),
]
