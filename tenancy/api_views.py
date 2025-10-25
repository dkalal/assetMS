"""
Tenancy API Views - Branch and Company API endpoints
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import Branch, Company


@login_required
@require_http_methods(["GET"])
def api_branches_list(request):
    """
    API endpoint to list all active branches for the current user's company.
    
    Returns:
        JSON response with list of branches including id, name, code, is_active
    """
    company = getattr(request, 'company', None) or getattr(request.user, 'company', None)
    
    if not company:
        return JsonResponse({
            'success': False,
            'error': 'Company context required'
        }, status=403)
    
    # Get all branches for the company
    branches = Branch.objects.filter(company=company).order_by('name')
    
    branches_data = []
    for branch in branches:
        branches_data.append({
            'id': branch.pk,
            'name': branch.name,
            'code': branch.code,
            'address': branch.address or '',
            'is_active': branch.is_active,
            'is_head_office': branch.is_head_office,
        })
    
    return JsonResponse({
        'success': True,
        'branches': branches_data,
        'total': len(branches_data)
    })
