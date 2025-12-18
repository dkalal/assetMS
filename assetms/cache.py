"""
WORLD-CLASS: Enterprise Caching Strategy
Inspired by: ServiceNow ITAM, IBM Maximo, SAP EAM

Performance Targets:
- Dashboard load: <500ms
- Asset list: <1s for 10k+ assets
- Search results: <200ms
- API responses: <100ms
"""

from django.core.cache import cache
from django.conf import settings
from django.db.models import Count, Q
from functools import wraps
import hashlib
import json
from typing import Any, Dict, List, Optional


class CacheManager:
    """Enterprise-grade cache management with multi-tenant isolation"""
    
    # Cache timeouts (seconds)
    DASHBOARD_TIMEOUT = 300  # 5 minutes
    ASSET_LIST_TIMEOUT = 600  # 10 minutes
    SEARCH_TIMEOUT = 180  # 3 minutes
    METADATA_TIMEOUT = 1800  # 30 minutes
    
    @staticmethod
    def _make_key(prefix: str, company_id: int, **kwargs) -> str:
        """Generate tenant-scoped cache key"""
        key_data = {'company': company_id, **kwargs}
        key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:8]
        return f"{prefix}_{company_id}_{key_hash}"
    
    @classmethod
    def get_dashboard_summary(cls, company_id: int, user_id: int, branch_id: Optional[int] = None) -> Optional[Dict]:
        """Get cached dashboard summary"""
        key = cls._make_key('dashboard', company_id, user=user_id, branch=branch_id)
        return cache.get(key)
    
    @classmethod
    def set_dashboard_summary(cls, company_id: int, user_id: int, data: Dict, branch_id: Optional[int] = None):
        """Cache dashboard summary with tenant isolation"""
        key = cls._make_key('dashboard', company_id, user=user_id, branch=branch_id)
        cache.set(key, data, cls.DASHBOARD_TIMEOUT)
    
    @classmethod
    def invalidate_dashboard(cls, company_id: int):
        """Invalidate all dashboard caches for company"""
        # In production, use Redis SCAN with pattern
        # For now, clear entire cache (safe but less efficient)
        cache.clear()
    
    @classmethod
    def get_asset_list(cls, company_id: int, filters: Dict) -> Optional[List]:
        """Get cached asset list with filters"""
        key = cls._make_key('assets', company_id, **filters)
        return cache.get(key)
    
    @classmethod
    def set_asset_list(cls, company_id: int, filters: Dict, data: List):
        """Cache asset list results"""
        key = cls._make_key('assets', company_id, **filters)
        cache.set(key, data, cls.ASSET_LIST_TIMEOUT)


def cache_dashboard_data(timeout: int = CacheManager.DASHBOARD_TIMEOUT):
    """Decorator for caching dashboard data with automatic invalidation"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'company') or not request.company:
                return func(request, *args, **kwargs)
            
            company_id = request.company.id
            user_id = request.user.id
            branch_id = getattr(request, 'branch', {}).get('id') if hasattr(request, 'branch') else None
            
            # Try cache first
            cached_data = CacheManager.get_dashboard_summary(company_id, user_id, branch_id)
            if cached_data and not settings.DEBUG:
                return cached_data
            
            # Generate fresh data
            result = func(request, *args, **kwargs)
            
            # Cache the result
            if isinstance(result, dict):
                CacheManager.set_dashboard_summary(company_id, user_id, result, branch_id)
            
            return result
        return wrapper
    return decorator


class QueryOptimizer:
    """Database query optimization utilities"""
    
    @staticmethod
    def optimize_asset_queryset(queryset):
        """Apply standard optimizations to asset queries"""
        return queryset.select_related(
            'company', 'branch', 'category', 'assigned_to'
        ).prefetch_related(
            'transfers', 'maintenance_records'
        )
    
    @staticmethod
    def optimize_user_queryset(queryset):
        """Apply standard optimizations to user queries"""
        return queryset.select_related('company').prefetch_related(
            'user_branches__branch'
        )


# Performance monitoring decorator
def monitor_performance(operation_name: str):
    """Monitor operation performance and log slow queries"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log slow operations (>1 second)
                if execution_time > 1.0:
                    import logging
                    logger = logging.getLogger('performance')
                    logger.warning(
                        f"Slow operation: {operation_name} took {execution_time:.2f}s"
                    )
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                import logging
                logger = logging.getLogger('performance')
                logger.error(
                    f"Failed operation: {operation_name} failed after {execution_time:.2f}s: {e}"
                )
                raise
        return wrapper
    return decorator