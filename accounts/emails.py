"""
Account Management Email Utilities
===================================
Purpose: Email sending functions for registration, verification, invitations
Uses Celery for async delivery
"""

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, user_id, verification_url):
    """
    Celery task to send email verification email.
    
    Args:
        user_id: User ID
        verification_url: Full verification URL
    """
    try:
        from users.models import User
        from smtplib import SMTPAuthenticationError
        
        user = User.objects.get(id=user_id)
        
        # Check email backend type
        email_backend = settings.EMAIL_BACKEND
        is_console_backend = 'console' in email_backend.lower() if email_backend else False
        
        subject = 'Verify Your Email - Asset Management System'
        
        # Render HTML email template
        html_message = render_to_string('emails/verify_email.html', {
            'user': user,
            'verification_url': verification_url,
            'company_name': user.company.name if user.company else 'Asset Management System',
        })
        
        # Plain text fallback
        plain_message = f"""
Hi {user.get_full_name() or user.username},

Thank you for creating an account with {user.company.name if user.company else 'Asset Management System'}.

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
Asset Management System Team
"""
        
        # Use fail_silently=True for console backend to prevent errors
        fail_silently = is_console_backend
        
        # For console backend, also print a clear message
        if is_console_backend:
            print("\n" + "="*80)
            print("📧 VERIFICATION EMAIL (Console Backend)")
            print("="*80)
            print(f"To: {user.email}")
            print(f"Subject: {subject}")
            print("-"*80)
            print(plain_message)
            print("-"*80)
            print(f"Verification URL: {verification_url}")
            print("="*80 + "\n")
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=fail_silently,
        )
        
        logger.info(f"Verification email sent to {user.email}")
        return True
        
    except SMTPAuthenticationError as e:
        # Don't retry on authentication errors - configuration issue
        logger.error(f"SMTP authentication error - check email credentials: {e}", exc_info=True)
        # Log but don't retry - user can check console or configure SMTP properly
        return False
    except Exception as e:
        logger.error(f"Error sending verification email: {e}", exc_info=True)
        # Only retry if not console backend and not authentication error
        if 'console' not in str(settings.EMAIL_BACKEND).lower() and self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)
        else:
            # Don't retry for console backend or after max retries
            logger.warning(f"Email sending failed, not retrying: {e}")
            return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_invitation_email_task(self, invitation_id):
    """
    Celery task to send user invitation email.
    
    Args:
        invitation_id: UserInvitation UUID
    """
    try:
        from .models import UserInvitation
        from django.urls import reverse
        from smtplib import SMTPAuthenticationError
        
        invitation = UserInvitation.objects.select_related('company', 'branch', 'invited_by').get(id=invitation_id)
        
        # Check email backend type
        email_backend = settings.EMAIL_BACKEND
        is_console_backend = 'console' in email_backend.lower() if email_backend else False
        
        # Build acceptance URL
        # Use settings to determine scheme and host
        scheme = 'https' if not settings.DEBUG else 'http'
        host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
        
        # Build URL manually since reverse needs request context
        try:
            path = reverse('accounts:accept_invitation', args=[invitation.invitation_token])
            acceptance_url = f"{scheme}://{host}{path}"
        except Exception:
            # Fallback if reverse fails
            acceptance_url = f"{scheme}://{host}/accounts/invitations/accept/{invitation.invitation_token}/"
        
        subject = f"You're Invited to Join {invitation.company.name}!"
        
        # Render HTML email template
        html_message = render_to_string('emails/invitation.html', {
            'invitation': invitation,
            'acceptance_url': acceptance_url,
            'inviter_name': invitation.invited_by.get_full_name() if invitation.invited_by else 'Administrator',
        })
        
        # Plain text fallback
        plain_message = f"""
Hi {invitation.first_name},

{invitation.invited_by.get_full_name() if invitation.invited_by else 'An administrator'} has invited you to join {invitation.company.name} on Asset Management System.

Your role will be: {invitation.get_role_display()}
Branch: {invitation.branch.name if invitation.branch else 'Not assigned'}

Click the link below to accept the invitation:
{acceptance_url}

This invitation will expire in 7 days.

If you didn't expect this invitation, please ignore this email.

Best regards,
Asset Management System Team
"""
        
        # Use fail_silently=True for console backend
        fail_silently = is_console_backend
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.email],
            html_message=html_message,
            fail_silently=fail_silently,
        )
        
        logger.info(f"Invitation email sent to {invitation.email}")
        return True
        
    except SMTPAuthenticationError as e:
        # Don't retry on authentication errors
        logger.error(f"SMTP authentication error - check email credentials: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Error sending invitation email: {e}", exc_info=True)
        # Only retry if not console backend and not authentication error
        if 'console' not in str(settings.EMAIL_BACKEND).lower() and self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)
        else:
            logger.warning(f"Email sending failed, not retrying: {e}")
            return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email_task(self, user_id):
    """
    Celery task to send welcome email after email verification.
    
    Args:
        user_id: User ID
    """
    try:
        from users.models import User
        from smtplib import SMTPAuthenticationError
        
        user = User.objects.select_related('company').get(id=user_id)
        
        # Check email backend type
        email_backend = settings.EMAIL_BACKEND
        is_console_backend = 'console' in email_backend.lower() if email_backend else False
        
        subject = f'Welcome to {user.company.name if user.company else "Asset Management System"}!'
        
        # Build dashboard URL
        scheme = 'https' if not settings.DEBUG else 'http'
        host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
        try:
            path = reverse('dashboard')
            dashboard_url = f"{scheme}://{host}{path}"
        except Exception:
            dashboard_url = f"{scheme}://{host}/dashboard/"
        
        # Render HTML email template
        html_message = render_to_string('emails/welcome.html', {
            'user': user,
            'company_name': user.company.name if user.company else 'Asset Management System',
            'dashboard_url': dashboard_url,
        })
        
        # Plain text fallback
        plain_message = f"""
Hi {user.get_full_name() or user.username},

Welcome to {user.company.name if user.company else 'Asset Management System'}!

Your email has been verified and your account is now active.

Get started by visiting your dashboard and registering your first asset.

If you have any questions, please don't hesitate to contact support.

Best regards,
Asset Management System Team
"""
        
        # Use fail_silently=True for console backend
        fail_silently = is_console_backend
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=fail_silently,
        )
        
        logger.info(f"Welcome email sent to {user.email}")
        return True
        
    except SMTPAuthenticationError as e:
        # Don't retry on authentication errors
        logger.error(f"SMTP authentication error - check email credentials: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}", exc_info=True)
        # Only retry if not console backend and not authentication error
        if 'console' not in str(settings.EMAIL_BACKEND).lower() and self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)
        else:
            logger.warning(f"Email sending failed, not retrying: {e}")
            return False


def send_verification_email(user, request=None):
    """
    Send email verification email to user.
    
    Args:
        user: User instance
        request: HttpRequest (for building absolute URL)
        
    Returns:
        tuple: (success: bool, verification_url: str, error: str or None)
    """
    from .utils import generate_secure_token
    
    # Generate verification token
    token = generate_secure_token(32)
    user.email_verification_token = token
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
    
    # Build verification URL
    if request:
        scheme = 'https' if request.is_secure() else 'http'
        host = request.get_host()
    else:
        scheme = 'https' if not settings.DEBUG else 'http'
        host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
    
    verification_url = f"{scheme}://{host}{reverse('accounts:verify_email', args=[token])}"
    
    # Check if using console backend - if so, send synchronously for immediate feedback
    is_console_backend = 'console' in str(settings.EMAIL_BACKEND).lower() if settings.EMAIL_BACKEND else False
    
    try:
        if is_console_backend:
            # In console mode, execute synchronously for immediate console output
            result = send_verification_email_task.apply(args=[user.id, verification_url])
            if result.successful():
                logger.info(f"Verification email sent to console for {user.email}")
                return True, verification_url, None
            else:
                logger.error(f"Failed to send verification email: {result.result}")
                return False, verification_url, str(result.result)
        else:
            # In SMTP mode, use async task
            send_verification_email_task.delay(user.id, verification_url)
            logger.info(f"Verification email task queued for {user.email}")
            return True, verification_url, None
    except Exception as e:
        logger.error(f"Error sending verification email: {e}", exc_info=True)
        return False, verification_url, str(e)


def send_invitation_email(invitation, request=None):
    """
    Send invitation email.
    
    Args:
        invitation: UserInvitation instance
        request: HttpRequest (for building absolute URL)
    """
    # Store request in task context if available
    # Note: Celery tasks don't have direct access to request, so we'll build URL in task
    try:
        send_invitation_email_task.delay(str(invitation.id))
        return True
    except Exception as e:
        logger.error(f"Error queueing invitation email task for {invitation.email}: {e}", exc_info=True)
        return False


def send_welcome_email(user):
    """
    Send welcome email after verification.
    
    Args:
        user: User instance
    """
    send_welcome_email_task.delay(user.id)

