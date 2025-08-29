from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.views.decorators.csrf import ensure_csrf_cookie

app_name = 'users'

urlpatterns = [
    # Authentication
    path('login/', views.EnterpriseLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('password/change-required/', views.PasswordChangeRequiredView.as_view(), name='password_change_required'),
    path('accept-invitation/<uuid:token>/', views.accept_invitation, name='accept_invitation'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
]
