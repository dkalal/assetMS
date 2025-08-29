from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import AuditLog
from users.models import User
from assets.models import Asset
from django.core.paginator import Paginator
from django.db.models import Q

# Create your views here.

@login_required
def audit_dashboard(request):
    logs = AuditLog.objects.select_related('user', 'asset').all()
    users = User.objects.all()
    assets = Asset.objects.all()
    actions = AuditLog.ACTION_CHOICES
    # Filtering
    user_id = request.GET.get('user')
    action = request.GET.get('action')
    asset_id = request.GET.get('asset')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action:
        logs = logs.filter(action=action)
    if asset_id:
        logs = logs.filter(asset_id=asset_id)
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)
    # Search
    search = request.GET.get('search')
    if search:
        logs = logs.filter(Q(details__icontains=search) | Q(asset__dynamic_data__icontains=search))
    logs = logs.order_by('-timestamp')
    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'audit/audit_dashboard.html', {
        'page_obj': page_obj,
        'users': users,
        'assets': assets,
        'actions': actions,
        'request': request,
    })
