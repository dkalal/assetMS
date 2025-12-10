from datetime import date, timedelta

from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib.auth import logout, get_user_model, authenticate
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth.views import PasswordChangeView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse_lazy

from .forms import UserProfileForm, PasswordResetEmailOrUsernameForm
from audit.utils import (
    log_login_success,
    log_login_failure,
    log_logout,
    log_account_lockout
)

class EmailAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form that accepts email or username.
    
    Modern SaaS standard: Email-based login (Slack, Asana, Salesforce)
    Backward compatible: Also supports username for legacy users
    """
    username = forms.CharField(
        label='Email or Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email or username',
            'autocomplete': 'username',
            'inputmode': 'email',  # mobile keyboard hint without enforcing email pattern
            'type': 'text',        # allow plain usernames
        }),
        help_text='Enter your email address or username'
    )
    
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update field labels for better UX
        self.fields['username'].label = 'Email or Username'
        self.fields['password'].label = 'Password'
    
    def clean_username(self):
        """
        Validate that the input looks like an email or username.
        """
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError('Please enter your email address or username.')
        return username


@method_decorator([ensure_csrf_cookie, csrf_protect, never_cache], name='dispatch')
class EnterpriseLoginView(LoginView):
    """
    Enterprise Login View with enhanced security features.
    
    Features:
    - Email-based login (modern SaaS standard)
    - CSRF protection
    - Audit logging for all login attempts
    - Failed login attempt tracking
    - Account lockout after threshold
    - Multi-tenancy support
    
    Following world-class standards: ServiceNow ITAM, IBM Maximo, SAP EAM, Slack, Asana
    """
    template_name = 'registration/login.html'
    form_class = EmailAuthenticationForm
    redirect_authenticated_user = True
    
    # Account lockout settings
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        redirect_field_name = self.redirect_field_name
        request = self.request
        redirect_to = request.POST.get(redirect_field_name) or request.GET.get(redirect_field_name)
        if redirect_to and not url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            redirect_to = ''
        context['redirect_field_name'] = redirect_field_name
        context['redirect_field_value'] = redirect_to
        return context
    
    def form_valid(self, form):
        """
        Called when login is successful.
        Logs the successful login and resets failed attempts.
        """
        user = form.get_user()
        
        # Reset failed login attempts on successful login
        if hasattr(user, 'failed_login_attempts') and user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.save(update_fields=['failed_login_attempts', 'account_locked_until'])
        
        # Log successful login
        log_login_success(user, self.request)
        
        # Call parent form_valid to complete login
        response = super().form_valid(form)

        # WORLD-CLASS: Remember-me session handling
        # If user selected "Remember me", extend session expiry to 30 days.
        # Otherwise, expire at browser close (enterprise security default).
        remember_me = self.request.POST.get('remember_me')
        try:
            if remember_me:
                # 30 days in seconds
                self.request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                # Expire when browser closes
                self.request.session.set_expiry(0)
        except Exception:
            # Never break login flow due to session expiry edge cases
            pass

        return response
    
    def form_invalid(self, form):
        """
        Called when login fails.
        Tracks failed attempts and implements account lockout.
        """
        # Get username/email from form data
        username_or_email = form.data.get('username', '')

        if username_or_email:
            User = get_user_model()
            try:
                # Try to find user by email or username (matches our backend)
                user = User.objects.get(
                    Q(email__iexact=username_or_email)
                    | Q(username__iexact=username_or_email)
                )

                # Check if account is currently locked
                if hasattr(user, 'account_locked_until') and user.account_locked_until:
                    if timezone.now() < user.account_locked_until:
                        # Account is still locked
                        remaining = (user.account_locked_until - timezone.now()).total_seconds() / 60
                        log_login_failure(
                            username_or_email,
                            self.request,
                            f'Account locked (remaining: {remaining:.0f} minutes)',
                        )
                        messages.error(
                            self.request,
                            'Account is locked due to multiple failed login attempts. '
                            f'Please try again in {remaining:.0f} minutes.',
                        )
                        return super().form_invalid(form)
                    else:
                        # Lockout period expired, reset counters
                        user.account_locked_until = None
                        user.failed_login_attempts = 0

                # Increment failed login attempts
                if hasattr(user, 'failed_login_attempts'):
                    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

                    # Check if we should lock the account
                    if user.failed_login_attempts >= self.MAX_FAILED_ATTEMPTS:
                        user.account_locked_until = timezone.now() + timedelta(
                            minutes=self.LOCKOUT_DURATION_MINUTES
                        )
                        user.save(
                            update_fields=['failed_login_attempts', 'account_locked_until']
                        )

                        # Log account lockout
                        log_account_lockout(
                            user, self.request, user.failed_login_attempts
                        )

                        messages.error(
                            self.request,
                            'Account locked due to '
                            f'{self.MAX_FAILED_ATTEMPTS} failed login attempts. '
                            f'Please try again in {self.LOCKOUT_DURATION_MINUTES} minutes.',
                        )
                    else:
                        user.save(update_fields=['failed_login_attempts'])
                        remaining_attempts = (
                            self.MAX_FAILED_ATTEMPTS - user.failed_login_attempts
                        )
                        messages.warning(
                            self.request,
                            'Invalid credentials. '
                            f'{remaining_attempts} attempts remaining before account lockout.',
                        )

                # Log failed login attempt
                log_login_failure(
                    username_or_email, self.request, 'Invalid credentials'
                )

            except User.DoesNotExist:
                # User doesn't exist - log but don't reveal this information
                log_login_failure(username_or_email, self.request, 'User not found')

        return super().form_invalid(form)


@method_decorator([ensure_csrf_cookie, csrf_protect, never_cache], name='dispatch')
class EnterprisePasswordResetView(PasswordResetView):
    """Multi-tenant password reset view with Celery delivery.

    The heavy lifting (multi-tenant user lookup, Celery dispatch, and
    audit logging) is implemented in PasswordResetEmailOrUsernameForm.save.
    This view simply wires the form to Django's auth flow and passes
    the request into the form for tenancy context.
    """

    form_class = PasswordResetEmailOrUsernameForm
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


@csrf_protect
@login_required
def profile(request):
    """User profile view with edit form handling"""
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('users:profile') if request.resolver_match and request.resolver_match.namespace == 'users' else redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=user)

    return render(request, 'users/profile.html', {
        'user_obj': user,
        'form': form,
    })


@login_required
def my_retirement_request(request):
    """Self-service retirement request page for the current user.

    - Enforces minimum notice period (2 weeks) via frontend
    - Scopes company context to the authenticated user for multi-tenancy
    - Renders the world-class retirement UI template
    """
    min_date = (date.today() + timedelta(days=14)).isoformat()

    context = {
        'min_date': min_date,
        'company': getattr(request.user, 'company', None),
    }

    return render(request, 'retirement/my_retirement.html', context)


@login_required
def retirement_approval_center(request):
    """Retirement approval center for managers and admins.
    
    - Only accessible to users with Manager or Admin role
    - Displays pending retirement requests for approval
    - Company-scoped for multi-tenancy
    """
    from users.models import User
    
    # Check if user has permission (Manager or Admin)
    if request.user.role not in [User.MANAGER, User.ADMIN]:
        from django.contrib import messages
        messages.error(request, 'You do not have permission to access the approval center.')
        return redirect('dashboard')
    
    context = {
        'company': getattr(request.user, 'company', None),
    }
    
    return render(request, 'retirement/approval_center.html', context)


@never_cache
def custom_logout(request):
    """
    WORLD-CLASS: Custom logout view with audit logging.
    
    Supports both GET (shows confirmation) and POST (performs logout)
    Following best practices from ServiceNow ITAM, IBM Maximo, SAP EAM
    
    Features:
    - Audit logging for logout events
    - Session duration tracking
    - CSRF protection
    - Global logout (dashboard + admin)
    
    Note: CSRF protection provided by CsrfViewMiddleware (global)
    GET requests show confirmation page, POST requests perform logout
    
    IMPORTANT: Logout is GLOBAL - logs out from both regular dashboard AND Django admin
    This is Django's standard behavior and matches industry best practices
    """
    if request.method == 'POST':
        # POST request: Perform logout (CSRF protected by middleware)
        # This logs out from BOTH regular dashboard and Django admin (single session)
        
        # Store user and calculate session duration before logout
        user = request.user
        username = user.username if user.is_authenticated else 'User'
        
        # Calculate session duration if possible
        session_duration = None
        if user.is_authenticated and user.last_login:
            session_duration = (timezone.now() - user.last_login).total_seconds()
        
        # Log logout event BEFORE performing logout
        if user.is_authenticated:
            log_logout(user, request, session_duration)
        
        # Perform Django logout (clears session, deletes session cookie)
        logout(request)
        
        # Success message
        messages.success(request, f'{username}, you have been successfully logged out from all interfaces.')
        
        # Redirect to login page
        response = redirect('users:login')
        
        # CRITICAL: Ensure session cookie is deleted
        # This prevents any lingering session issues
        response.delete_cookie('sessionid')
        response.delete_cookie('csrftoken')
        
        return response
    
    # GET request: Show logout confirmation page
    # This handles direct URL access (e.g., typing /users/logout/ in browser)
    return render(request, 'registration/logout_confirm.html')

@method_decorator([login_required, csrf_protect, never_cache], name='dispatch')
class PasswordChangeRequiredView(PasswordChangeView):
    template_name = 'registration/password_change_required.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        # Clear the enforcement flag after successful change
        user = self.request.user
        try:
            if hasattr(user, 'force_password_change') and user.force_password_change:
                user.force_password_change = False
                user.save(update_fields=['force_password_change'])
        except Exception:
            pass
        messages.success(self.request, 'Password updated. Welcome back!')
        # Redirect to dashboard or profile
        return redirect('dashboard')

@csrf_protect
@never_cache
def accept_invitation(request, token):
    """Accept invitation link, set password, activate account."""
    User = get_user_model()
    user = User.objects.filter(invitation_token=str(token), is_active=False).first()
    if not user:
        messages.error(request, 'Invalid or expired invitation link.')
        return render(request, 'users/accept_invitation.html', { 'invalid': True })

    # Enforce invitation expiry based on session_timeout_minutes (from invite form)
    try:
        from django.utils import timezone
        from datetime import timedelta
        if user.invitation_sent_at:
            expiry_time = user.invitation_sent_at + timedelta(minutes=user.session_timeout_minutes or 60)
            if timezone.now() > expiry_time:
                messages.error(request, 'This invitation link has expired. Please contact an administrator for a new invite.')
                return render(request, 'users/accept_invitation.html', { 'invalid': True })
    except Exception:
        pass

    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if not password1 or not password2:
            messages.error(request, 'Please enter and confirm your password.')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match.')
        else:
            try:
                validate_password(password1, user)
                user.set_password(password1)
                user.is_active = True
                # Clear invitation fields
                user.invitation_token = None
                user.is_invited = False
                user.force_password_change = False
                user.save()
                messages.success(request, 'Your account has been activated. Please log in.')
                return redirect('users:login')
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))

    return render(request, 'users/accept_invitation.html', {
        'email': user.email,
        'full_name': user.get_full_name() or user.username,
        'token': token,
    })

@login_required
@require_http_methods(["GET"])
def api_user_list(request):
    """API endpoint to list users for staff management"""
    User = get_user_model()
    
    # Check if user is admin
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin')):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get users from same company (multi-tenancy)
    users = User.objects.filter(company=request.user.company).select_related('branch', 'company')
    
    # Build user list
    user_list = []
    for user in users:
        # Get initials
        initials = ''
        if user.first_name and user.last_name:
            initials = f"{user.first_name[0]}{user.last_name[0]}".upper()
        elif user.username:
            initials = user.username[:2].upper()
        
        # Check if user is online (active in last 15 minutes)
        is_online = False
        if hasattr(user, 'last_activity') and user.last_activity:
            is_online = (timezone.now() - user.last_activity).total_seconds() < 900
        
        # Format last login
        last_login = 'Never'
        if user.last_login:
            last_login = user.last_login.strftime('%b %d, %Y %I:%M %p')
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.username,
            'initials': initials,
            'role': user.role if hasattr(user, 'role') else 'user',
            'branch_id': user.branch.id if user.branch else None,
            'branch_name': user.branch.name if user.branch else None,
            'is_active': user.is_active,
            'is_invited': user.is_invited if hasattr(user, 'is_invited') else False,
            'is_online': is_online,
            'last_login': last_login,
            'avatar': user.avatar.url if hasattr(user, 'avatar') and user.avatar else None,
        }
        user_list.append(user_data)
    
    return JsonResponse({
        'success': True,
        'users': user_list,
        'total': len(user_list)
    })


@login_required
def my_transfer_requests(request):
    """
    My Transfer Requests Page
    
    Display user's own branch transfer requests with statistics.
    
    WORLD-CLASS: Clean, accessible, user-friendly interface.
    
    Features:
    - View all user's transfer requests
    - Real-time statistics
    - Status tracking
    - Action buttons
    - Responsive design
    """
    from tenancy.models import Branch
    
    # Get available branches for transfer (exclude current branch)
    available_branches = Branch.objects.filter(
        company=request.user.company,
        is_active=True
    ).exclude(
        id=request.user.primary_branch.id if request.user.primary_branch else None
    ).order_by('name')
    
    context = {
        'available_branches': available_branches,
    }
    
    return render(request, 'users/my_transfer_requests.html', context)