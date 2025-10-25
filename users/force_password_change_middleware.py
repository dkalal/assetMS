from django.http import JsonResponse
from django.shortcuts import redirect

# Users URLs are included at root ('') in assetms/urls.py, so allowed paths should be root-based
ALLOWED_PATH_PREFIXES = (
    '/password/change-required/',
    '/users/password/change-required/',
    '/logout/',
    '/users/logout/',
    '/login/',
    '/users/login/',
    '/admin/login/',
    '/static/',
    '/media/',
)


class ForcePasswordChangeMiddleware:
    """
    Redirect authenticated users flagged with force_password_change to the
    password change page. Blocks API access with a 403 JSON until changed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path or ''

        if user and user.is_authenticated:
            if getattr(user, 'force_password_change', False):
                # Allow safe paths
                if not path.startswith(ALLOWED_PATH_PREFIXES):
                    # Block API access until password updated
                    if path.startswith('/api/'):
                        return JsonResponse({
                            'success': False,
                            'error': 'Password change required',
                            'detail': 'Please update your password to continue.'
                        }, status=403)
                    # Redirect any other page to password change required
                    return redirect('users:password_change_required')

        return self.get_response(request)
