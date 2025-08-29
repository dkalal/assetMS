from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import PasswordChangeView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from .forms import UserProfileForm

@method_decorator([ensure_csrf_cookie, csrf_protect, never_cache], name='dispatch')
class EnterpriseLoginView(LoginView):
    """Enterprise Login View with enhanced CSRF protection"""
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['csrf_token'] = self.request.META.get('CSRF_COOKIE')
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

@csrf_protect
@never_cache
def custom_logout(request):
    """Custom logout view with proper CSRF handling"""
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('users:login')
    
    return redirect('dashboard')

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