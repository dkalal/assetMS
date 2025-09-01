def get_client_ip(request):
    """
    Get the client's IP address from the request.
    Handles various HTTP headers to get the real IP behind proxies.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the first IP in the list (client IP, not proxy)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# --- Permission helpers (enterprise, minimal integration) ---
from typing import Set, Dict
from django.core.cache import cache
from django.utils import timezone

try:
    from .models import RolePermissionMatrix
except Exception:  # pragma: no cover - keep utils import-safe during migrations
    RolePermissionMatrix = None  # type: ignore

MATRIX_CACHE_KEY = 'users:role_permission_matrix:v1'
MATRIX_TTL_SECONDS = 60  # short TTL to reflect updates quickly; adjust in future

def _load_matrix() -> Dict[str, Set[str]]:
    """Load and cache the role-permission matrix as {role: set(codes)}."""
    if RolePermissionMatrix is None:
        # Fallback defaults if model unavailable
        default = {
            'Admin': {'view_assets', 'create_assets', 'edit_assets', 'delete_assets', 'manage_users', 'view_reports', 'export_data', 'system_admin'},
            'Manager': {'view_assets', 'create_assets', 'edit_assets', 'view_reports', 'export_data'},
            'User': {'view_assets'},
        }
        return default

    cached = cache.get(MATRIX_CACHE_KEY)
    if cached:
        return cached

    obj = RolePermissionMatrix.load()
    matrix = {role: set(perms or []) for role, perms in (obj.permissions or {}).items()}
    # Ensure keys
    for r in ('Admin', 'Manager', 'User'):
        matrix.setdefault(r, set())
    cache.set(MATRIX_CACHE_KEY, matrix, MATRIX_TTL_SECONDS)
    return matrix

def can(user, permission_code: str) -> bool:
    """Check if a user has a given logical permission code per RolePermissionMatrix.

    Rules:
    - Superuser always allowed.
    - Prefer explicit user.role ('admin'|'manager'|'user');
      fallback: staff -> 'Manager', else 'User'.
    - Empty/unknown codes return False.
    """
    if not permission_code or not isinstance(permission_code, str):
        return False
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True

    # Prefer explicit role from custom User model
    role_value = str(getattr(user, 'role', '') or '').lower()
    if role_value in ('admin', 'manager', 'user'):
        role = role_value.title()  # 'Admin'|'Manager'|'User'
    else:
        # Legacy/compat fallback using is_staff
        role = 'Manager' if getattr(user, 'is_staff', False) else 'User'
    matrix = _load_matrix()
    perms = matrix.get(role, set())
    return permission_code.strip() in perms

def invalidate_permissions_cache():
    """Invalidate cached RolePermissionMatrix (call after updates)."""
    cache.delete(MATRIX_CACHE_KEY)
