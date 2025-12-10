"""
Account Management Views
=========================
Purpose: Views for registration, email verification, onboarding, invitations
"""

import logging
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, TemplateView, ListView, DetailView
from django.urls import reverse
from django.http import JsonResponse, Http404

from .forms import (
    RegistrationForm,
    EmailVerificationForm,
    InvitationForm,
    BulkInvitationForm,
    InvitationAcceptanceForm,
    OnboardingStep1Form,
    OnboardingStep2Form,
)
from .models import UserInvitation, CompanyRegistration, OnboardingProgress
from .decorators import rate_limit_registration, email_verification_required, company_required
from .emails import send_verification_email, send_invitation_email, send_welcome_email
from .utils import is_token_expired, generate_secure_token
from tenancy.models import Company, Branch, UserBranch

User = get_user_model()
logger = logging.getLogger(__name__)


# ==========================
# Scenario 1: Self-Service Signup
# ==========================

@never_cache
@rate_limit_registration(limit=5, window_seconds=3600)
@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    Self-service registration view.
    
    Creates: Company, Branch, User, UserBranch, CompanyRegistration, OnboardingProgress
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Create Company
                    company = Company.objects.create(
                        name=form.cleaned_data['company_name']
                    )
                    
                    # 2. Create Head Office Branch
                    branch = Branch.objects.create(
                        company=company,
                        name='Head Office',
                        code='HQ',
                        is_head_office=True,
                        is_active=True
                    )
                    
                    # 3. Create User
                    user = User.objects.create_user(
                        username=form.cleaned_data['email'],  # Use email as username
                        email=form.cleaned_data['email'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        password=form.cleaned_data['password'],
                    )
                    # Set custom fields after creation
                    user.company = company
                    user.role = User.ADMIN
                    user.email_verified = False  # Will be verified via email
                    user.save(update_fields=['company', 'role', 'email_verified'])
                    
                    # 4. Create UserBranch (primary)
                    UserBranch.ensure_primary(user, company, branch)
                    
                    # 5. Create CompanyRegistration
                    registration = CompanyRegistration.objects.create(
                        company=company,
                        plan=form.cleaned_data['plan'],
                        billing_email=form.cleaned_data['email'],
                        subscription_status='trial',
                    )
                    
                    # 6. Create OnboardingProgress
                    OnboardingProgress.objects.create(
                        user=user,
                        current_step=1,
                    )
                    
                    # 7. Send verification email (non-blocking - don't fail registration if email fails)
                    email_sent = False
                    verification_url = None
                    is_console_backend = 'console' in str(settings.EMAIL_BACKEND).lower() if settings.EMAIL_BACKEND else False
                    
                    try:
                        success, verification_url, error = send_verification_email(user, request)
                        if success:
                            logger.info(f"Verification email sent to {user.email}")
                            email_sent = True
                        else:
                            logger.warning(f"Verification email sending returned False: {error}")
                            # Still consider it sent for console backend
                            if is_console_backend:
                                email_sent = True
                    except Exception as email_error:
                        logger.error(f"Failed to send verification email: {email_error}", exc_info=True)
                        # Don't fail registration if email fails - user can request resend
                        # For console backend, email still prints to console even if exception occurs
                        if is_console_backend:
                            email_sent = True  # Console backend prints to console
                    
                    logger.info(f"New registration: {user.email} for company {company.name}")
                    
                    # Persist verification context for the verify-email page
                    if verification_url:
                        request.session['verification_url'] = verification_url
                    request.session['verification_email'] = user.email
                    request.session['verification_console'] = is_console_backend
                    
                    if email_sent:
                        if is_console_backend:
                            messages.success(
                                request,
                                'Registration successful! Please check the console/terminal or use the link shown on the next page.'
                            )
                        else:
                            messages.success(
                                request,
                                'Registration successful! Please check your email to verify your account.'
                            )
                    else:
                        messages.warning(
                            request,
                            'Registration successful, but we couldn\'t send the verification email. '
                            'You can use the link on the next page or request a new verification email from the login page.'
                        )
                    
                    return redirect('accounts:verify_email_sent')
                    
            except Exception as e:
                logger.error(f"Registration error: {e}", exc_info=True)
                # Show detailed error in DEBUG mode for troubleshooting
                error_message = 'An error occurred during registration. Please try again or contact support.'
                if settings.DEBUG:
                    error_message += f' Error: {str(e)}'
                messages.error(request, error_message)
    else:
        form = RegistrationForm()
    
    return render(request, 'accounts/register.html', {
        'form': form,
    })


@never_cache
@require_http_methods(["GET"])
def verify_email_view(request, token):
    """
    Email verification view.
    
    Validates token and marks email as verified.
    """
    try:
        user = User.objects.get(email_verification_token=token)
    except User.DoesNotExist:
        messages.error(request, 'Invalid or expired verification link.')
        return redirect('accounts:register')
    
    # Check if already verified
    if user.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('accounts:onboarding')
    
    # Check if token expired
    if is_token_expired(user.email_verification_sent_at, expiry_hours=24):
        messages.error(request, 'Verification link has expired. Please request a new one.')
        return redirect('accounts:resend_verification')
    
    # Verify email
    user.email_verified = True
    user.email_verification_token = ''  # Clear token (single-use)
    user.save(update_fields=['email_verified', 'email_verification_token'])
    
    # Auto-login user
    login(request, user)
    
    # Send welcome email
    send_welcome_email(user)
    
    messages.success(request, 'Email verified successfully! Welcome to Asset Management System.')
    
    # Redirect to onboarding
    return redirect('accounts:onboarding')


@never_cache
@require_http_methods(["GET", "POST"])
def verify_email_sent_view(request):
    """
    Display page after sending verification email.
    Shows verification link directly for console backend.
    """
    from django.conf import settings
    
    # Check if email backend is console (for development)
    is_console_backend = 'console' in str(settings.EMAIL_BACKEND).lower() if settings.EMAIL_BACKEND else False
    
    verification_url = request.session.pop('verification_url', None)
    user_email = request.session.pop('verification_email', None)
    session_console_flag = request.session.pop('verification_console', None)
    if session_console_flag is not None:
        is_console_backend = session_console_flag
    
    if request.method == 'POST':
        # Resend verification email
        form = EmailVerificationForm(request.POST)
        
        if form.is_valid():
            try:
                user = User.objects.get(email=form.cleaned_data['email'])
                user_email = user.email
                
                # Send verification email and get result
                success, verification_url, error = send_verification_email(user, request)
                
                if success:
                    if is_console_backend:
                        messages.success(
                            request, 
                            'Verification email sent to console! The verification link is shown below.'
                        )
                    else:
                        messages.success(request, 'Verification email sent! Please check your inbox.')
                else:
                    # Error occurred
                    if is_console_backend:
                        # For console backend, show link anyway (email might have printed)
                        messages.warning(
                            request,
                            f'Email sending had an issue, but here is your verification link. Error: {error}'
                        )
                    else:
                        # For SMTP, show error with helpful message
                        error_msg = 'Failed to send email. '
                        if error and 'SMTPAuthenticationError' in error:
                            error_msg += 'Email server authentication failed. Please check email configuration or contact support.'
                        elif error:
                            error_msg += f'Error: {error}. Please try again or contact support.'
                        else:
                            error_msg += 'Please try again or contact support.'
                        messages.error(request, error_msg)
                
                # Don't redirect - show the link on the same page
                
            except User.DoesNotExist:
                messages.error(request, 'No account found with this email address.')
            except Exception as e:
                logger.error(f"Error in verify_email_sent_view: {e}", exc_info=True)
                messages.error(request, 'An error occurred. Please try again.')
    else:
        form = EmailVerificationForm()
        
        # If user just registered and we don't have a session value, try to get their verification URL
        if not verification_url and request.user.is_authenticated and not request.user.email_verified:
            user = request.user
            user_email = user.email
            if user.email_verification_token:
                scheme = 'https' if request.is_secure() else 'http'
                host = request.get_host()
                verification_url = f"{scheme}://{host}{reverse('accounts:verify_email', args=[user.email_verification_token])}"
    
    return render(request, 'accounts/verify_email_sent.html', {
        'form': form,
        'verification_url': verification_url,
        'is_console_backend': is_console_backend,
        'user_email': user_email,
    })


@never_cache
@email_verification_required
@require_http_methods(["GET", "POST"])
def onboarding_wizard_view(request):
    """
    Onboarding wizard view (3 steps).
    
    Steps:
    1. Company details (industry, size, timezone)
    2. Invite team (optional)
    3. Quick tour (feature overview)
    """
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    try:
        progress = request.user.onboarding
    except OnboardingProgress.DoesNotExist:
        # Create if doesn't exist
        progress = OnboardingProgress.objects.create(user=request.user, current_step=1)
    
    # Handle skip
    if request.GET.get('skip') == 'true':
        progress.skip_onboarding()
        messages.info(request, 'Onboarding skipped. You can complete it later from settings.')
        return redirect('dashboard')
    
    # Handle step submission
    if request.method == 'POST':
        step = int(request.POST.get('step', progress.current_step))
        
        if step == 1:
            form = OnboardingStep1Form(request.POST)
            if form.is_valid():
                # Update company metadata (store in Company model or separate model)
                company = request.user.company
                if company:
                    # Store in metadata JSON field if available
                    if hasattr(company, 'metadata'):
                        company.metadata.update({
                            'industry': form.cleaned_data.get('industry', ''),
                            'company_size': form.cleaned_data.get('company_size', ''),
                            'timezone': form.cleaned_data.get('timezone', ''),
                        })
                        company.save(update_fields=['metadata'])
                
                progress.company_details_completed = True
                progress.advance_to_next_step()
                progress.save()
                
                messages.success(request, 'Company details saved!')
                return redirect('accounts:onboarding')
        
        elif step == 2:
            form = OnboardingStep2Form(request.POST)
            if form.is_valid():
                invite_team = form.cleaned_data.get('invite_team', False)
                emails = form.cleaned_data.get('emails', [])
                
                if invite_team and emails:
                    # Send invitations
                    company = request.user.company
                    for email in emails:
                        try:
                            invitation = UserInvitation.objects.create(
                                company=company,
                                email=email,
                                first_name='',  # Will be filled on acceptance
                                last_name='',
                                role=User.USER,
                                branch=request.user.primary_branch,
                                invited_by=request.user,
                            )
                            send_invitation_email(invitation, request)
                        except Exception as e:
                            logger.error(f"Error sending invitation to {email}: {e}")
                    
                    progress.team_invited = True
                    messages.success(request, f'Invitations sent to {len(emails)} team members!')
                
                progress.advance_to_next_step()
                progress.save()
                
                return redirect('accounts:onboarding')
        
        elif step == 3:
            # Tour completed
            progress.tour_completed = True
            progress.mark_completed()
            
            messages.success(request, 'Onboarding completed! Welcome to Asset Management System.')
            return redirect('dashboard')
    
    # Display current step
    step = progress.current_step
    
    if step == 1:
        form = OnboardingStep1Form()
        template = 'accounts/onboarding_step1.html'
    elif step == 2:
        form = OnboardingStep2Form()
        template = 'accounts/onboarding_step2.html'
    elif step == 3:
        form = None
        template = 'accounts/onboarding_step3.html'
    else:
        # Completed
        return redirect('dashboard')
    
    return render(request, template, {
        'form': form,
        'progress': progress,
        'current_step': step,
    })


# ==========================
# Scenario 2: User Invitations
# ==========================

@company_required
@require_http_methods(["GET", "POST"])
def send_invitation_view(request):
    """
    Send user invitation view.
    
    Supports single and bulk invitations.
    """
    if request.user.role not in [User.ADMIN, User.MANAGER]:
        messages.error(request, 'Only admins and managers can send invitations.')
        return redirect('dashboard')
    
    company = request.user.company
    
    # Check if company can add more users
    try:
        registration = CompanyRegistration.objects.get(company=company)
        if not registration.can_add_user():
            messages.error(
                request,
                f'User limit reached ({registration.max_users} users). Please upgrade your plan.'
            )
            return redirect('dashboard')
    except CompanyRegistration.DoesNotExist:
        pass  # Allow if no registration (free tier)
    
    if request.method == 'POST':
        # Check if bulk invitation
        if 'bulk' in request.POST:
            form = BulkInvitationForm(request.POST, company=company)
            
            if form.is_valid():
                emails = form.cleaned_data['emails']
                role = form.cleaned_data['role']
                branch = form.cleaned_data.get('branch')
                
                sent_count = 0
                errors = []
                
                for email in emails:
                    try:
                        invitation = UserInvitation.objects.create(
                            company=company,
                            email=email,
                            first_name='',  # Will be filled on acceptance
                            last_name='',
                            role=role,
                            branch=branch,
                            invited_by=request.user,
                        )
                        send_invitation_email(invitation, request)
                        sent_count += 1
                    except Exception as e:
                        errors.append(f"{email}: {str(e)}")
                        logger.error(f"Error creating invitation for {email}: {e}")
                
                if sent_count > 0:
                    messages.success(request, f'Successfully sent {sent_count} invitation(s)!')
                if errors:
                    messages.warning(request, f'Some invitations failed: {", ".join(errors[:5])}')
                
                return redirect('accounts:invitation_list')
        else:
            # Single invitation
            form = InvitationForm(request.POST, company=company, invited_by=request.user)
            
            if form.is_valid():
                invitation = form.save(commit=False)
                invitation.company = company
                invitation.invited_by = request.user
                invitation.save()
                
                send_invitation_email(invitation, request)
                
                messages.success(request, f'Invitation sent to {invitation.email}!')
                return redirect('accounts:invitation_list')
    else:
        form = InvitationForm(company=company, invited_by=request.user)
    
    bulk_form = BulkInvitationForm(company=company)
    
    return render(request, 'accounts/send_invitation.html', {
        'form': form,
        'bulk_form': bulk_form,
    })


@never_cache
@require_http_methods(["GET", "POST"])
def accept_invitation_view(request, token):
    """
    Accept invitation view.
    
    User sets password and account is created.
    """
    try:
        invitation = UserInvitation.objects.select_related('company', 'branch').get(
            invitation_token=token
        )
    except UserInvitation.DoesNotExist:
        messages.error(request, 'Invalid invitation link.')
        return redirect('users:login')
    
    # Check if already accepted
    if invitation.status == 'accepted':
        messages.info(request, 'This invitation has already been accepted.')
        return redirect('users:login')
    
    # Check if expired
    if not invitation.is_valid():
        invitation.mark_expired()
        messages.error(request, 'This invitation has expired. Please request a new one.')
        return redirect('users:login')
    
    # Check if cancelled
    if invitation.status == 'cancelled':
        messages.error(request, 'This invitation has been cancelled.')
        return redirect('users:login')
    
    if request.method == 'POST':
        form = InvitationAcceptanceForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create user
                    user = User.objects.create_user(
                        username=invitation.email,
                        email=invitation.email,
                        first_name=invitation.first_name,
                        last_name=invitation.last_name,
                        password=form.cleaned_data['password'],
                        company=invitation.company,
                        role=invitation.role,
                        email_verified=True,  # Invited users don't need email verification
                        onboarding_completed=True,  # Skip onboarding for invited users
                    )
                    
                    # Create UserBranch
                    branch = invitation.branch or invitation.company.branches.filter(
                        is_head_office=True
                    ).first()
                    
                    if branch:
                        UserBranch.ensure_primary(user, invitation.company, branch)
                    
                    # Create OnboardingProgress (marked as completed)
                    OnboardingProgress.objects.create(
                        user=user,
                        company_details_completed=True,
                        tour_completed=True,
                        completed_at=timezone.now(),
                        current_step=4,
                    )
                    
                    # Mark invitation as accepted
                    invitation.accept(user)
                    
                    # Auto-login
                    login(request, user)
                    
                    logger.info(f"Invitation accepted: {user.email} for company {invitation.company.name}")
                    
                    messages.success(
                        request,
                        f'Welcome to {invitation.company.name}! Your account has been created.'
                    )
                    
                    return redirect('dashboard')
                    
            except Exception as e:
                logger.error(f"Error accepting invitation: {e}", exc_info=True)
                messages.error(
                    request,
                    'An error occurred. Please try again or contact support.'
                )
    else:
        form = InvitationAcceptanceForm()
    
    return render(request, 'accounts/accept_invitation.html', {
        'form': form,
        'invitation': invitation,
    })


@company_required
@require_http_methods(["GET"])
def invitation_list_view(request):
    """
    List all invitations for company.
    """
    if request.user.role not in [User.ADMIN, User.MANAGER]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company
    invitations = UserInvitation.objects.filter(
        company=company
    ).select_related('branch', 'invited_by').order_by('-sent_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        invitations = invitations.filter(status=status_filter)
    
    return render(request, 'accounts/invitation_list.html', {
        'invitations': invitations,
        'status_filter': status_filter,
    })


@company_required
@require_http_methods(["POST"])
def resend_invitation_view(request, pk):
    """
    Resend invitation email.
    """
    if request.user.role not in [User.ADMIN, User.MANAGER]:
        messages.error(request, 'Access denied.')
        return redirect('accounts:invitation_list')
    
    invitation = get_object_or_404(
        UserInvitation,
        id=pk,
        company=request.user.company
    )
    
    if invitation.status != 'pending':
        messages.error(request, 'Can only resend pending invitations.')
        return redirect('accounts:invitation_list')
    
    send_invitation_email(invitation, request)
    messages.success(request, f'Invitation resent to {invitation.email}!')
    
    return redirect('accounts:invitation_list')


@company_required
@require_http_methods(["POST"])
def cancel_invitation_view(request, pk):
    """
    Cancel pending invitation.
    """
    if request.user.role not in [User.ADMIN, User.MANAGER]:
        messages.error(request, 'Access denied.')
        return redirect('accounts:invitation_list')
    
    invitation = get_object_or_404(
        UserInvitation,
        id=pk,
        company=request.user.company
    )
    
    if invitation.cancel():
        messages.success(request, 'Invitation cancelled.')
    else:
        messages.error(request, 'Can only cancel pending invitations.')
    
    return redirect('accounts:invitation_list')

