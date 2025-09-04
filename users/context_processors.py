from typing import Dict


def user_view_data(request) -> Dict[str, object]:
    """Context processor that provides a consistent avatar URL and display name for templates.

    Returns keys:
      - current_user: the authenticated user or None
      - avatar_url: URL to user's avatar or empty string
      - display_name: full name or username
    """
    user = getattr(request, 'user', None)
    avatar_url = ''
    display_name = ''
    if user and user.is_authenticated:
        display_name = getattr(user, 'get_full_name', None)() if hasattr(user, 'get_full_name') else getattr(user, 'username', '')
        profile_image = getattr(user, 'profile_image', None)
        try:
            if profile_image and hasattr(profile_image, 'url'):
                avatar_url = profile_image.url
        except Exception:
            avatar_url = ''

    return {
        'current_user': user,
        'avatar_url': avatar_url,
        'display_name': display_name,
    }
