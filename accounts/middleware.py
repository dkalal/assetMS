"""
Trial Status Middleware
=======================
Purpose: Check trial status on every request and display warnings
Pattern: SaaS best practice (Asana, Slack, Salesforce)

Features:
- Display trial expiry warnings in UI
- Block access for expired trials
- Graceful degradation
- Performance optimized (cached)
"""

from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from accounts.models import CompanyRegistration


class TrialStatusMiddleware(MiddlewareMixin):
    """
    Check trial status and display warnings
    
    Behavior:
    - Active trial (>7 days): No message
    - Warning (≤7 days): Yellow banner
    - Expired (≤0 days): Red banner + limited access
    - Suspended: Block access, show upgrade page
    """
    
    # URLs that don't require trial check
    EXEMPT_URLS = [
        '/login/',
        '/logout/',
        '/admin/',
        '/static/',
        '/media/',
        '/trial-expired/',
        '/upgrade/',
    ]
    
    def process_request(self, request):
        # Skip if user not authenticated
        if not request.user.is_authenticated:
            return None
        
        # Skip if system admin (no company)
        if request.user.is_system_admin and not request.user.company:
            return None
        
        # Skip exempt URLs
        path = request.path
        if any(path.startswith(url) for url in self.EXEMPT_URLS):
            return None
        
        # Skip if no company assigned
        if not request.user.company:
            return None
        
        # Get company registration (cached for 5 minutes)
        cache_key = f'trial_status_{request.user.company.id}'
        trial_status = cache.get(cache_key)
        
        if trial_status is None:
            try:
                registration = CompanyRegistration.objects.get(company=request.user.company)
                
                # Only check if on trial
                if registration.subscription_status == 'trial':
                    days_left = registration.days_until_trial_ends()
                    
                    if days_left is not None:
                        if days_left <= 0:
                            trial_status = 'expired'
                        elif days_left <= 7:
                            trial_status = 'warning'
                        else:
                            trial_status = 'active'
                    else:
                        trial_status = 'active'
                elif registration.subscription_status == 'suspended':
                    trial_status = 'suspended'
                else:
                    trial_status = 'paid'
                
                # Cache for 5 minutes
                cache.set(cache_key, trial_status, 300)
                
            except CompanyRegistration.DoesNotExist:
                # No registration = free access (for now)
                trial_status = 'active'
                cache.set(cache_key, trial_status, 300)
        
        # Store in request for template access
        request.trial_status = trial_status
        
        # Handle suspended accounts
        if trial_status == 'suspended':
            return render(request, 'accounts/trial_suspended.html', {
                'company': request.user.company,
            }, status=403)
        
        # Handle expired trials (soft block - show warning but allow access)
        if trial_status == 'expired':
            # Add persistent warning message
            if not request.session.get('trial_expired_warning_shown'):
                messages.error(
                    request,
                    "Your trial has expired. Please contact support to continue using the system.",
                    extra_tags='trial-expired'
                )
                request.session['trial_expired_warning_shown'] = True
        
        # Handle warning period
        elif trial_status == 'warning':
            try:
                registration = CompanyRegistration.objects.get(company=request.user.company)
                days_left = registration.days_until_trial_ends()
                
                if days_left is not None and not request.session.get('trial_warning_shown'):
                    messages.warning(
                        request,
                        f"Your trial expires in {days_left} days. Contact support to upgrade.",
                        extra_tags='trial-warning'
                    )
                    request.session['trial_warning_shown'] = True
            except CompanyRegistration.DoesNotExist:
                pass
        
        return None
    
    def process_response(self, request, response):
        # Add trial status to response headers (for debugging)
        if hasattr(request, 'trial_status'):
            response['X-Trial-Status'] = request.trial_status
        
        return response
