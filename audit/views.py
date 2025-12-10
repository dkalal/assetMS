from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import AuditLog
from users.models import User
from assets.models import Asset
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from tenancy.mixins import company_required
import json

# Create your views here.

@login_required
@company_required
def audit_dashboard(request):
    """
    World-class audit dashboard with multi-tenancy, statistics, and advanced filtering.
    Matches main dashboard quality standards.
    """
    # Multi-tenancy: Scope to company
    company = request.company
    
    # Base queryset with optimized queries
    logs = AuditLog.objects.filter(company=company).select_related(
        'user', 'asset', 'branch'
    )
    
    # Get filter options (company-scoped)
    users = User.objects.filter(company=company).order_by('first_name', 'last_name')
    # Asset model doesn't have 'name' field - use asset_tag or category__name
    assets = Asset.objects.filter(company=company).select_related('category').order_by('category__name', 'asset_tag')
    actions = AuditLog.ACTION_CHOICES
    
    # Apply filters
    user_id = request.GET.get('user')
    action = request.GET.get('action')
    asset_id = request.GET.get('asset')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')
    
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action:
        logs = logs.filter(action=action)
    if asset_id:
        logs = logs.filter(asset_id=asset_id)
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__lte=date_to + ' 23:59:59')
    if search:
        logs = logs.filter(
            Q(details__icontains=search) | 
            Q(asset__name__icontains=search) |
            Q(user__username__icontains=search)
        )
    
    # Order by most recent
    logs = logs.order_by('-timestamp')
    
    # Calculate statistics
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    
    # Action distribution for chart (last 30 days)
    action_distribution = logs.filter(timestamp__gte=thirty_days_ago).values('action').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Convert to dict for easy template access
    action_counts = {item['action']: item['count'] for item in action_distribution}
    
    stats = {
        'total_activities': logs.filter(timestamp__gte=thirty_days_ago).count(),
        'today_activities': logs.filter(timestamp__gte=today_start).count(),
        'active_users': logs.filter(timestamp__gte=week_start).values('user').distinct().count(),
        'critical_events': logs.filter(
            action__in=['delete', 'edit'],
            timestamp__gte=thirty_days_ago
        ).count(),
        'action_counts': action_counts,
    }
    
    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'users': users,
        'assets': assets,
        'actions': actions,
        'stats': stats,
        'action_counts_json': json.dumps(action_counts),  # JSON for JavaScript
        'request': request,
    }
    
    return render(request, 'audit/audit_dashboard_worldclass.html', context)
