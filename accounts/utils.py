"""
Account utilities
 - Token generation and expiry helpers
 - Email and password validation
 - Simple IP-based rate limiting
"""

import secrets
from datetime import timedelta

from django.core.cache import cache
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone


def generate_secure_token(length: int = 32) -> str:
    """Generate a URL-safe token with the requested length."""
    # token_urlsafe returns ~1.3 chars per byte; overshoot then trim
    raw = secrets.token_urlsafe(length)
    return raw[:length]


def is_token_expired(sent_at, expiry_hours: int = 24) -> bool:
    """Return True if the token sent time is older than expiry_hours."""
    if not sent_at:
        return True
    return timezone.now() > sent_at + timedelta(hours=expiry_hours)


def validate_email_format(email: str) -> bool:
    """Validate email format using Django's EmailValidator."""
    try:
        EmailValidator()(email)
        return True
    except ValidationError:
        return False


def validate_password_strength(password: str):
    """
    Validate password using Django's configured validators.
    Returns (is_valid: bool, errors: list[str])
    """
    try:
        validate_password(password)
        return True, []
    except ValidationError as exc:
        return False, list(exc.messages)


def get_client_ip(request):
    """Extract client IP from request headers safely."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or 'unknown'


def check_rate_limit(key: str, limit: int, window_seconds: int):
    """
    Basic sliding-window-ish rate limit using cache.
    Returns (is_allowed: bool, remaining: int, reset_time: int seconds).
    """
    # Use cache incr with expiry; if not exists, set to 1 with TTL
    current = cache.get(key)
    if current is None:
        cache.set(key, 1, timeout=window_seconds)
        return True, limit - 1, window_seconds

    if current >= limit:
        # Rate limit exceeded
        # Approximate reset time from remaining TTL
        ttl = cache.ttl(key)
        reset = ttl if ttl and ttl > 0 else window_seconds
        return False, 0, reset

    new_count = cache.incr(key)
    ttl = cache.ttl(key)
    reset = ttl if ttl and ttl > 0 else window_seconds
    return True, max(limit - new_count, 0), reset




