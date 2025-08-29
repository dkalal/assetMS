from django.core.cache import cache
from django.conf import settings
import hashlib

class PermissionCache:
    """Enterprise-level permission caching system"""
    
    CACHE_TIMEOUT = getattr(settings, 'PERMISSION_CACHE_TIMEOUT', 3600)  # 1 hour
    
    @classmethod
    def get_cache_key(cls, user_id, permission_type='all'):
        """Generate cache key for user permissions"""
        return f"user_permissions:{user_id}:{permission_type}"
    
    @classmethod
    def get_user_permissions(cls, user):
        """Get cached user permissions"""
        cache_key = cls.get_cache_key(user.id)
        permissions = cache.get(cache_key)
        
        if permissions is None:
            from .permissions import UserPermissionManager
            permissions = UserPermissionManager.get_user_permissions_summary(user)
            cache.set(cache_key, permissions, cls.CACHE_TIMEOUT)
        
        return permissions
    
    @classmethod
    def invalidate_user_permissions(cls, user_id):
        """Invalidate cached permissions for user"""
        cache_key = cls.get_cache_key(user_id)
        cache.delete(cache_key)
    
    @classmethod
    def invalidate_all_permissions(cls):
        """Invalidate all permission caches"""
        # This would require a more sophisticated cache backend
        # For now, we'll use a simple approach
        cache.clear()