from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import PasswordChangeView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .forms import UserProfileForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

@method_decorator([ensure_csrf_cookie, csrf_protect, never_cache], name='dispatch')
class EnterpriseLoginView(LoginView):
    """Enterprise Login View with enhanced CSRF protection"""
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
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

@never_cache
def custom_logout(request):
    """
    WORLD-CLASS: Custom logout view with proper CSRF handling
    
    Supports both GET (shows confirmation) and POST (performs logout)
    Following best practices from ServiceNow ITAM, IBM Maximo, SAP EAM
    
    Note: CSRF protection provided by CsrfViewMiddleware (global)
    GET requests show confirmation page, POST requests perform logout
    
    IMPORTANT: Logout is GLOBAL - logs out from both regular dashboard AND Django admin
    This is Django's standard behavior and matches industry best practices
    """
    if request.method == 'POST':
        # POST request: Perform logout (CSRF protected by middleware)
        # This logs out from BOTH regular dashboard and Django admin (single session)
        
        # Store username for message
        username = request.user.username if request.user.is_authenticated else 'User'
        
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