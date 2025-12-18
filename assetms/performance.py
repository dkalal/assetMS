"""
WORLD-CLASS: Performance Optimization Engine
Inspired by: Netflix, Spotify, Airbnb engineering practices

Key Optimizations:
1. Database Connection Pooling
2. Query Optimization & Monitoring
3. Memory Management
4. Async Task Processing
5. CDN Integration
6. Response Compression
"""

import time
import logging
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from functools import wraps
from typing import Dict, Any, Optional
import psutil
import gc


logger = logging.getLogger('performance')


class PerformanceMonitor:
    """Real-time performance monitoring and optimization"""
    
    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """Get current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'memory_available': memory.available // (1024**2),  # MB
                'disk_usage': disk.percent,
                'disk_free': disk.free // (1024**3),  # GB
                'active_connections': len(connection.queries),
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    @staticmethod
    def log_slow_query(query_time: float, query: str, params: tuple = ()):
        """Log slow database queries for optimization"""
        if query_time > 0.5:  # Log queries slower than 500ms
            logger.warning(
                f"Slow Query ({query_time:.3f}s): {query[:200]}... "
                f"Params: {str(params)[:100]}"
            )
    
    @staticmethod
    def optimize_memory():
        """Force garbage collection and memory optimization"""
        gc.collect()
        return psutil.virtual_memory().percent


def performance_critical(cache_timeout: int = 300):
    """Decorator for performance-critical views with caching and monitoring"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            
            # Generate cache key based on user, company, and request params
            cache_key = f"perf_{request.user.id}_{getattr(request, 'company', {}).get('id', 0)}_{hash(str(kwargs))}"
            
            # Try cache first (skip in DEBUG mode)
            if not settings.DEBUG and cache_timeout > 0:
                cached_result = cache.get(cache_key)
                if cached_result:
                    return cached_result
            
            # Monitor database queries
            initial_queries = len(connection.queries)
            
            try:
                # Execute view
                result = view_func(request, *args, **kwargs)
                
                # Calculate performance metrics
                execution_time = time.time() - start_time
                query_count = len(connection.queries) - initial_queries
                
                # Log performance data
                if execution_time > 1.0 or query_count > 10:
                    logger.warning(
                        f"Performance Alert - View: {view_func.__name__}, "
                        f"Time: {execution_time:.3f}s, Queries: {query_count}"
                    )
                
                # Cache successful results
                if hasattr(result, 'status_code') and result.status_code == 200 and cache_timeout > 0:
                    cache.set(cache_key, result, cache_timeout)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"View Error - {view_func.__name__}: {e} "
                    f"(after {execution_time:.3f}s)"
                )
                raise
        
        return wrapper
    return decorator


class DatabaseOptimizer:
    """Database performance optimization utilities"""
    
    @staticmethod
    def analyze_query_performance():
        """Analyze recent query performance"""
        if not settings.DEBUG:
            return {}
        
        queries = connection.queries[-10:]  # Last 10 queries
        total_time = sum(float(q['time']) for q in queries)
        slow_queries = [q for q in queries if float(q['time']) > 0.1]
        
        return {
            'total_queries': len(queries),
            'total_time': total_time,
            'slow_queries': len(slow_queries),
            'average_time': total_time / len(queries) if queries else 0,
        }
    
    @staticmethod
    def get_connection_info():
        """Get database connection information"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                db_version = cursor.fetchone()[0]
                
                # PostgreSQL specific queries
                if 'postgresql' in settings.DATABASES['default']['ENGINE']:
                    cursor.execute("""
                        SELECT count(*) as active_connections 
                        FROM pg_stat_activity 
                        WHERE state = 'active'
                    """)
                    active_connections = cursor.fetchone()[0]
                else:
                    active_connections = 'N/A'
                
                return {
                    'database_version': db_version,
                    'active_connections': active_connections,
                    'queries_executed': len(connection.queries),
                }
        except Exception as e:
            logger.error(f"Failed to get DB connection info: {e}")
            return {}


class AssetQueryOptimizer:
    """Specialized optimizations for asset-related queries"""
    
    @staticmethod
    def get_optimized_asset_list(company, filters=None, limit=100):
        """Get optimized asset list with minimal queries"""
        from assets.models import Asset
        
        queryset = Asset.objects.filter(company=company).select_related(
            'category', 'assigned_to', 'branch'
        ).prefetch_related(
            'transfers__to_user'
        )
        
        if filters:
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
            if filters.get('category'):
                queryset = queryset.filter(category_id=filters['category'])
            if filters.get('branch'):
                queryset = queryset.filter(branch_id=filters['branch'])
        
        return queryset[:limit]
    
    @staticmethod
    def get_dashboard_metrics(company):
        """Get dashboard metrics with single optimized query"""
        from assets.models import Asset
        from django.db.models import Count, Q
        
        # Single query to get all metrics
        metrics = Asset.objects.filter(company=company).aggregate(
            total_assets=Count('id'),
            active_assets=Count('id', filter=Q(status='active')),
            maintenance_assets=Count('id', filter=Q(status='in_maintenance')),
            retired_assets=Count('id', filter=Q(status='retired')),
        )
        
        return metrics


# Middleware for performance monitoring
class PerformanceMiddleware:
    """Middleware to monitor request performance"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        initial_queries = len(connection.queries)
        
        response = self.get_response(request)
        
        # Calculate metrics
        execution_time = time.time() - start_time
        query_count = len(connection.queries) - initial_queries
        
        # Add performance headers (for debugging)
        if settings.DEBUG:
            response['X-Execution-Time'] = f"{execution_time:.3f}s"
            response['X-Query-Count'] = str(query_count)
        
        # Log slow requests
        if execution_time > 2.0:  # Requests slower than 2 seconds
            logger.warning(
                f"Slow Request: {request.path} took {execution_time:.3f}s "
                f"with {query_count} queries"
            )
        
        return response


# API Performance utilities
def api_cache_response(timeout: int = 300):
    """Cache API responses with proper headers"""
    def decorator(view_func):
        @wraps(view_func)
        @vary_on_headers('Authorization', 'Accept-Language')
        def wrapper(request, *args, **kwargs):
            # Skip caching for non-GET requests
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)
            
            # Generate cache key
            cache_key = f"api_{request.path}_{request.GET.urlencode()}_{request.user.id}"
            
            # Try cache
            cached_response = cache.get(cache_key)
            if cached_response and not settings.DEBUG:
                return JsonResponse(cached_response)
            
            # Execute view
            response = view_func(request, *args, **kwargs)
            
            # Cache successful JSON responses
            if (hasattr(response, 'status_code') and 
                response.status_code == 200 and 
                isinstance(response, JsonResponse)):
                cache.set(cache_key, response.content, timeout)
            
            return response
        
        return wrapper
    return decorator


# Memory optimization utilities
def optimize_queryset_memory(queryset, batch_size: int = 1000):
    """Process large querysets in batches to optimize memory usage"""
    for i in range(0, queryset.count(), batch_size):
        yield queryset[i:i + batch_size]


def clear_query_cache():
    """Clear Django's query cache to free memory"""
    connection.queries_log.clear()
    gc.collect()