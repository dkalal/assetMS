"""
Global Search View - World-Class Multi-Entity Search
Searches across Assets, Users, and Categories with intelligent ranking
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_GET
from django.contrib.auth import get_user_model

from assets.models import Asset, AssetCategory
from tenancy.models import Branch

User = get_user_model()


@require_GET
@login_required
def global_search_api(request):
    """
    World-class global search across multiple entities.
    
    Searches:
    - Assets (name, description, UUID, dynamic_data)
    - Users (username, first_name, last_name, email)
    - Categories (name, description)
    
    Returns ranked results with entity type and relevance.
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({
            'success': False,
            'error': 'Search query must be at least 2 characters',
            'results': []
        })
    
    # Get user's company for multi-tenancy
    user = request.user
    company = getattr(user, 'company', None)
    
    if not company:
        return JsonResponse({
            'success': False,
            'error': 'Company context required',
            'results': []
        })
    
    results = []
    
    # 1. SEARCH ASSETS
    try:
        asset_qs = Asset.objects.filter(company=company).select_related(
            'category', 'branch', 'assigned_to'
        )
        
        # Build search query for assets
        asset_q = Q(uuid__icontains=query)  # UUID search
        
        # Search in dynamic_data (JSON field) - check if 'name' field contains query
        asset_q |= Q(dynamic_data__name__icontains=query)
        asset_q |= Q(description__icontains=query)
        asset_q |= Q(category__name__icontains=query)
        
        assets = asset_qs.filter(asset_q).distinct()[:10]  # Limit to 10 results
        
        for asset in assets:
            asset_name = asset.dynamic_data.get('name', f'{asset.category.name} Asset')
            results.append({
                'type': 'asset',
                'id': str(asset.uuid),
                'title': asset_name,
                'subtitle': f'{asset.category.name} • {asset.get_status_display()}',
                'url': f'/assets/{asset.uuid}/',
                'icon': 'box-seam',
                'badge': asset.get_status_display(),
                'badge_class': get_asset_badge_class(asset.status),
            })
    except Exception as e:
        # Log error but continue with other searches
        print(f"Asset search error: {e}")
    
    # 2. SEARCH USERS
    try:
        # Only search users in same company
        user_qs = User.objects.filter(
            company=company,
            is_active=True
        ).select_related('company')
        
        user_q = (
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
        
        users = user_qs.filter(user_q).distinct()[:10]
        
        for usr in users:
            full_name = usr.get_full_name() or usr.username
            results.append({
                'type': 'user',
                'id': usr.id,
                'title': full_name,
                'subtitle': f'{usr.email} • {usr.get_role_display()}',
                'url': f'/users/profile/{usr.id}/',
                'icon': 'person-circle',
                'badge': usr.get_role_display(),
                'badge_class': get_user_badge_class(usr.role),
            })
    except Exception as e:
        print(f"User search error: {e}")
    
    # 3. SEARCH CATEGORIES
    try:
        category_qs = AssetCategory.objects.filter(
            company=company
        ).annotate(
            asset_count=Count('assets')
        )
        
        category_q = (
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
        
        categories = category_qs.filter(category_q).distinct()[:10]
        
        for category in categories:
            results.append({
                'type': 'category',
                'id': category.id,
                'title': category.name,
                'subtitle': f'{category.asset_count} assets',
                'url': f'/categories/',  # Categories page with filter
                'icon': 'folder',
                'badge': f'{category.asset_count} assets',
                'badge_class': 'bg-info',
            })
    except Exception as e:
        print(f"Category search error: {e}")
    
    # 4. SEARCH BRANCHES (if user has access)
    try:
        if user.role in ['admin', 'manager']:
            branch_qs = Branch.objects.filter(
                company=company,
                is_active=True
            ).annotate(
                asset_count=Count('assets')
            )
            
            branch_q = (
                Q(name__icontains=query) |
                Q(address__icontains=query) |
                Q(city__icontains=query)
            )
            
            branches = branch_qs.filter(branch_q).distinct()[:5]
            
            for branch in branches:
                results.append({
                    'type': 'branch',
                    'id': branch.id,
                    'title': branch.name,
                    'subtitle': f'{branch.city} • {branch.asset_count} assets',
                    'url': f'/assets/?branch={branch.id}',
                    'icon': 'geo-alt',
                    'badge': f'{branch.asset_count} assets',
                    'badge_class': 'bg-success',
                })
    except Exception as e:
        print(f"Branch search error: {e}")
    
    # Sort results by relevance (exact matches first)
    def relevance_score(item):
        title_lower = item['title'].lower()
        query_lower = query.lower()
        
        # Exact match = highest score
        if title_lower == query_lower:
            return 0
        # Starts with query = high score
        elif title_lower.startswith(query_lower):
            return 1
        # Contains query = medium score
        elif query_lower in title_lower:
            return 2
        # Other matches = low score
        else:
            return 3
    
    results.sort(key=relevance_score)
    
    return JsonResponse({
        'success': True,
        'query': query,
        'count': len(results),
        'results': results[:20]  # Limit total results to 20
    })


def get_asset_badge_class(status):
    """Return Bootstrap badge class for asset status."""
    status_map = {
        'active': 'bg-success',
        'in_maintenance': 'bg-warning text-dark',
        'retired': 'bg-secondary',
        'lost': 'bg-danger',
        'deleted': 'bg-danger text-white',
        'transferred': 'bg-info',
    }
    return status_map.get(status, 'bg-primary')


def get_user_badge_class(role):
    """Return Bootstrap badge class for user role."""
    role_map = {
        'admin': 'bg-danger',
        'manager': 'bg-warning text-dark',
        'user': 'bg-primary',
    }
    return role_map.get(role, 'bg-secondary')
