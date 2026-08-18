"""
System Admin Views
==================
Purpose: Views for system-level administration
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator
from django.db import transaction

from .decorators import system_admin_required
from tenancy.models import Company, Branch
from accounts.models import CompanyRegistration, UserInvitation
from accounts.emails import send_invitation_email
from assets.models import Asset
from users.models import User

logger = logging.getLogger(__name__)


@system_admin_required
@require_http_methods(["GET"])
def system_dashboard_view(request):
    """
    System dashboard showing system-wide metrics.
    """
    # System metrics
    total_companies = Company.objects.count()
    total_users = User.objects.filter(company__isnull=False).count()
    total_assets = Asset.objects.count()
    
    # Active subscriptions
    active_subscriptions = CompanyRegistration.objects.filter(
        subscription_status__in=['trial', 'active']
    ).count()
    
    # Companies by plan
    companies_by_plan = CompanyRegistration.objects.values('plan').annotate(
        count=Count('id')
    ).order_by('plan')
    
    # Recent companies (last 10)
    recent_companies = Company.objects.select_related('registration').order_by('-created_at')[:10]
    
    context = {
        'total_companies': total_companies,
        'total_users': total_users,
        'total_assets': total_assets,
        'active_subscriptions': active_subscriptions,
        'companies_by_plan': companies_by_plan,
        'recent_companies': recent_companies,
    }
    
    return render(request, 'system_admin/dashboard.html', context)


@system_admin_required
@require_http_methods(["GET"])
def company_list_view(request):
    """
    List all companies with search and filter.
    """
    companies = Company.objects.select_related('registration').annotate(
        user_count=Count('users'),
        asset_count=Count('assets'),
        branch_count=Count('branches'),
    ).order_by('-created_at')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        companies = companies.filter(
            Q(name__icontains=search_query) |
            Q(registration__billing_email__icontains=search_query)
        )
    
    # Filter by subscription status
    status_filter = request.GET.get('status')
    if status_filter:
        companies = companies.filter(registration__subscription_status=status_filter)
    
    # Pagination
    paginator = Paginator(companies, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'system_admin/company_list.html', context)


@system_admin_required
@require_http_methods(["GET", "POST"])
def create_company_view(request):
    """
    Create a new company (system admin only).
    """
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        admin_email = request.POST.get('admin_email')
        admin_first_name = request.POST.get('admin_first_name')
        admin_last_name = request.POST.get('admin_last_name')
        plan = request.POST.get('plan', 'free')
        
        if not all([company_name, admin_email, admin_first_name, admin_last_name]):
            messages.error(request, 'All fields are required.')
            return redirect('system_admin:create_company')
        
        company = None
        invitation = None
        try:
            with transaction.atomic():
                # Create company
                company = Company.objects.create(name=company_name)
                
                # Create head office branch
                branch = Branch.objects.create(
                    company=company,
                    name='Head Office',
                    code='HQ',
                    is_head_office=True,
                    is_active=True
                )
                
                # Create admin user
                user = User.objects.create_user(
                    username=admin_email,
                    email=admin_email,
                    first_name=admin_first_name,
                    last_name=admin_last_name,
                    company=company,
                    role=User.ADMIN,
                    email_verified=True,  # System admin created users are pre-verified
                )
                
                # Set password (temporary - should be changed on first login)
                from django.contrib.auth.hashers import make_password
                user.password = make_password('TempPassword123!')
                user.force_password_change = True
                user.save()
                
                # Create UserBranch
                from tenancy.models import UserBranch
                UserBranch.ensure_primary(user, company, branch)
                
                # Create CompanyRegistration
                CompanyRegistration.objects.create(
                    company=company,
                    plan=plan,
                    billing_email=admin_email,
                    subscription_status='trial',
                )
                
                # Send invitation email to admin (invitation record)
                invitation = UserInvitation.objects.create(
                    company=company,
                    email=admin_email,
                    first_name=admin_first_name,
                    last_name=admin_last_name,
                    role=User.ADMIN,
                    branch=branch,
                    invited_by=None,  # System created
                )
        except Exception as e:
            logger.error(f"Error creating company: {e}", exc_info=True)
            messages.error(request, f'Error creating company: {str(e)}')
        else:
            # Only attempt to send email after the transaction has committed successfully
            try:
                send_invitation_email(invitation, request)
                messages.success(request, f'Company {company_name} created successfully!')
            except Exception as email_error:
                logger.error(
                    f"Error sending invitation email for company {company_name}: {email_error}",
                    exc_info=True,
                )
                messages.warning(
                    request,
                    f'Company {company_name} was created, but the invitation email could not be sent. '
                    'Please verify email settings or resend the invitation from the admin panel.',
                )
            return redirect('system_admin:company_detail', pk=company.id)
    
    return render(request, 'system_admin/create_company.html')


@system_admin_required
@require_http_methods(["GET"])
def company_detail_view(request, pk):
    """
    View company details and manage company.
    """
    company = get_object_or_404(
        Company.objects.select_related('registration').prefetch_related(
            'users', 'branches', 'assets'
        ),
        pk=pk
    )
    
    # Get company statistics
    user_count = company.users.count()
    asset_count = company.assets.count()
    branch_count = company.branches.count()
    
    # Recent activity (placeholder - can be enhanced with audit logs)
    recent_users = company.users.order_by('-date_joined')[:10]
    
    context = {
        'company': company,
        'user_count': user_count,
        'asset_count': asset_count,
        'branch_count': branch_count,
        'recent_users': recent_users,
    }
    
    return render(request, 'system_admin/company_detail.html', context)


@system_admin_required
@require_http_methods(["POST"])
def suspend_company_view(request, pk):
    """
    Suspend a company.
    """
    company = get_object_or_404(Company, pk=pk)
    
    try:
        registration = company.registration
        registration.subscription_status = 'suspended'
        registration.save()
        
        # Deactivate all users
        company.users.update(is_active=False)
        
        messages.success(request, f'Company {company.name} has been suspended.')
    except CompanyRegistration.DoesNotExist:
        messages.error(request, 'Company registration not found.')
    
    return redirect('system_admin:company_detail', pk=pk)


@system_admin_required
@require_http_methods(["POST"])
def reactivate_company_view(request, pk):
    """
    Reactivate a suspended company.
    """
    company = get_object_or_404(Company, pk=pk)
    
    try:
        registration = company.registration
        registration.subscription_status = 'active'
        registration.save()
        
        # Reactivate all users
        company.users.update(is_active=True)
        
        messages.success(request, f'Company {company.name} has been reactivated.')
    except CompanyRegistration.DoesNotExist:
        messages.error(request, 'Company registration not found.')
    
    return redirect('system_admin:company_detail', pk=pk)


@system_admin_required
@require_http_methods(["GET", "POST"])
def impersonate_user_view(request, user_id):
    """
    Impersonate a user for support purposes.
    """
    user = get_object_or_404(User, id=user_id)
    
    if not user.company:
        messages.error(request, 'Cannot impersonate system admin or users without company.')
        return redirect('system_admin:company_list')
    
    if request.method == 'POST':
        # Store original user in session
        request.session['impersonating_user_id'] = request.user.id
        request.session['impersonated_user_id'] = user.id
        
        # Log impersonation
        try:
            from audit.utils import log_audit
            log_audit(
                user=request.user,
                action='impersonate_user',
                resource_type='user',
                resource_id=user.id,
                details={'impersonated_user': user.email}
            )
        except Exception:
            pass  # Continue even if audit logging fails
        
        # Actually log in as the user
        from django.contrib.auth import login
        login(request, user)
        
        messages.info(request, f'Now impersonating {user.get_full_name() or user.username}.')
        return redirect('dashboard')
    
    context = {
        'target_user': user,
    }
    
    return render(request, 'system_admin/impersonate_confirm.html', context)


@system_admin_required
@require_http_methods(["POST"])
def exit_impersonation_view(request):
    """
    Exit user impersonation.
    """
    if 'impersonating_user_id' in request.session:
        del request.session['impersonating_user_id']
        del request.session['impersonated_user_id']
        messages.success(request, 'Exited impersonation mode.')
    
    return redirect('system_admin:dashboard')


@system_admin_required
@require_http_methods(["GET"])
def role_permissions_view(request):
    """System-level Role & Permission management UI.

    The actual RolePermissionMatrix is read and written via the
    /api/roles/permissions/ endpoint in users.api_views, which is further
    restricted to global operators (superuser or is_system_admin).
    This view only serves the HTML shell for the admin console.
    """
    return render(request, 'system_admin/role_permissions.html')

