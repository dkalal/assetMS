"""
Celery Tasks for User Management

Async tasks for:
- Session cleanup
- Password reset emails
- Account notifications
- User activity monitoring

Following best practices from ServiceNow ITAM, IBM Maximo, SAP EAM
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.utils import timezone

from .models import User
from tenancy.models import Alert

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def cleanup_expired_sessions(self):
    """
    Cleanup expired sessions
    Runs daily at 3 AM
    """
    try:
        # Delete expired sessions
        Session.objects.filter(expire_date__lt=timezone.now()).delete()
        
        logger.info("Expired sessions cleaned up")
        
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {e}", exc_info=True)


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(
    self,
    user_id,
    subject,
    template,
    html_template=None,
    context=None,
    from_email=None,
):
    """Send password reset email using Django templates.

    Args:
        user_id: ID of the user who will receive the email.
        subject: Email subject line.
        template: Django template path for the email body.
        context: Context dictionary for template rendering (without user).
        from_email: Optional from email override.
    """
    try:
        from django.template.loader import render_to_string

        user = User.objects.select_related('company').get(id=user_id)

        # Ensure we have a recipient address
        if not user.email:
            logger.warning("Skipping password reset email for user %s (no email configured)", user_id)
            return

        from_email = from_email or settings.DEFAULT_FROM_EMAIL

        # Build context, injecting user instance inside the task (not over the wire)
        email_context = {'user': user}
        if context:
            email_context.update(context)

        # Render plain-text body
        message = render_to_string(template, email_context)

        # Render optional HTML body
        html_message = None
        if html_template:
            html_message = render_to_string(html_template, email_context)

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=html_message,
        )

        logger.info("Password reset email sent to %s", user.email)

    except User.DoesNotExist:
        logger.error("User %s not found when sending password reset email", user_id)
    except Exception as e:
        logger.error("Error sending password reset email: %s", e, exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def send_account_locked_notification(self, user_id):
    """
    Notify user and admins when account is locked
    
    Args:
        user_id: User ID
    """
    try:
        user = User.objects.select_related('company').get(id=user_id)
        
        # Notify user
        if user.email:
            subject = f"[{user.company.name if user.company else 'AssetMS'}] Account Locked"
            message = f"""
            Hello {user.get_full_name() or user.username},
            
            Your account has been locked due to multiple failed login attempts.
            
            Please contact your administrator to unlock your account.
            
            Best regards,
            AssetMS Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        
        # Notify admins
        if user.company:
            admins = User.objects.filter(company=user.company, role='admin')
            
            for admin in admins:
                Alert.objects.create(
                    company=user.company,
                    user=admin,
                    level=Alert.LEVEL_WARNING,
                    title="User Account Locked",
                    message=f"User {user.username} account locked due to failed login attempts",
                    context={'user_id': user.id}
                )
        
        logger.info(f"Account locked notification sent for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error sending account locked notification: {e}", exc_info=True)


@shared_task(bind=True)
def cleanup_old_login_attempts(self):
    """
    Reset failed login attempts for users (older than 7 days)
    Runs daily
    
    Note: System uses failed_login_attempts field on User model
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        
        # Reset failed login attempts for users who haven't logged in recently
        updated_count = User.objects.filter(
            failed_login_attempts__gt=0,
            last_login__lt=cutoff_date
        ).update(failed_login_attempts=0)
        
        logger.info(f"Reset failed login attempts for {updated_count} users")
        
    except Exception as e:
        logger.error(f"Error resetting failed login attempts: {e}", exc_info=True)


@shared_task(bind=True)
def send_welcome_email(self, user_id):
    """
    Send welcome email to new user
    
    Args:
        user_id: User ID
    """
    try:
        user = User.objects.select_related('company').get(id=user_id)
        
        subject = f"Welcome to {user.company.name if user.company else 'AssetMS'}"
        message = f"""
        Hello {user.get_full_name() or user.username},
        
        Welcome to the Asset Management System!
        
        Your account has been created with the following details:
        - Username: {user.username}
        - Email: {user.email}
        - Role: {user.get_role_display()}
        
        Please log in and change your password on first login.
        
        Best regards,
        AssetMS Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        
        logger.info(f"Welcome email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}", exc_info=True)
