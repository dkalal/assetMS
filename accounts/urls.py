"""
Account Management URLs
=======================
Purpose: URL patterns for registration, verification, onboarding, invitations
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Registration & Email Verification
    path('register/', views.register_view, name='register'),
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('verify-email-sent/', views.verify_email_sent_view, name='verify_email_sent'),
    path('resend-verification/', views.verify_email_sent_view, name='resend_verification'),
    
    # Onboarding
    path('onboarding/', views.onboarding_wizard_view, name='onboarding'),
    
    # Invitations
    path('invitations/send/', views.send_invitation_view, name='send_invitation'),
    path('invitations/accept/<str:token>/', views.accept_invitation_view, name='accept_invitation'),
    path('invitations/', views.invitation_list_view, name='invitation_list'),
    path('invitations/<uuid:pk>/resend/', views.resend_invitation_view, name='resend_invitation'),
    path('invitations/<uuid:pk>/cancel/', views.cancel_invitation_view, name='cancel_invitation'),
]







