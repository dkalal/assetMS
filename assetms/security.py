"""
WORLD-CLASS: Enterprise Security Framework
Compliance: SOX, GDPR, ISO 27001, NIST Cybersecurity Framework

Security Layers:
1. Authentication & Authorization (Zero Trust)
2. Data Encryption (at rest & in transit)
3. Audit Logging & Monitoring
4. Input Validation & Sanitization
5. Rate Limiting & DDoS Protection
6. Security Headers & CSP
"""

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.contrib.auth import get_user_model
from functools import wraps
import logging
import json
from typing import Dict, Any, Optional, List


logger = logging.getLogger('security')
User = get_user_model()


class SecurityManager:
    """Enterprise security management and threat detection"""
    
    # Security thresholds
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes
    SUSPICIOUS_ACTIVITY_THRESHOLD = 10
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
        """Hash sensitive data with salt for storage"""
        if not salt:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA-256 (Django's default)
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            data.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return f"{salt}:{hashed.hex()}"
    
    @staticmethod
    def verify_hashed_data(data: str, hashed_data: str) -> bool:
        """Verify hashed sensitive data"""
        try:
            salt, hash_hex = hashed_data.split(':', 1)
            expected_hash = hashlib.pbkdf2_hmac(
                'sha256',
                data.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return hmac.compare_digest(expected_hash.hex(), hash_hex)
        except (ValueError, AttributeError):
            return False
    
    @classmethod
    def track_login_attempt(cls, username: str, ip_address: str, success: bool) -> Dict[str, Any]:
        """Track login attempts for security monitoring"""
        cache_key = f"login_attempts_{username}_{ip_address}"
        attempts = cache.get(cache_key, [])
        
        # Add current attempt
        attempt = {
            'timestamp': time.time(),
            'success': success,
            'ip': ip_address
        }
        attempts.append(attempt)
        
        # Keep only recent attempts (last hour)
        cutoff = time.time() - 3600
        attempts = [a for a in attempts if a['timestamp'] > cutoff]
        
        # Count failed attempts
        failed_attempts = len([a for a in attempts if not a['success']])
        
        # Check if account should be locked
        is_locked = failed_attempts >= cls.MAX_LOGIN_ATTEMPTS
        
        if is_locked:
            cache.set(cache_key, attempts, cls.LOCKOUT_DURATION)
            logger.warning(
                f"Account locked: {username} from {ip_address} "
                f"({failed_attempts} failed attempts)"
            )
        else:
            cache.set(cache_key, attempts, 3600)
        
        return {
            'failed_attempts': failed_attempts,
            'is_locked': is_locked,
            'lockout_expires': time.time() + cls.LOCKOUT_DURATION if is_locked else None
        }
    
    @classmethod
    def is_account_locked(cls, username: str, ip_address: str) -> bool:
        """Check if account is currently locked"""
        cache_key = f"login_attempts_{username}_{ip_address}"
        attempts = cache.get(cache_key, [])
        
        failed_attempts = len([a for a in attempts if not a['success']])
        return failed_attempts >= cls.MAX_LOGIN_ATTEMPTS
    
    @staticmethod
    def detect_suspicious_activity(user_id: int, activity_type: str, metadata: Dict = None) -> bool:
        """Detect suspicious user activity patterns"""
        cache_key = f"activity_{user_id}_{activity_type}"
        activities = cache.get(cache_key, [])
        
        # Add current activity
        activity = {
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        activities.append(activity)
        
        # Keep only recent activities (last 10 minutes)
        cutoff = time.time() - 600
        activities = [a for a in activities if a['timestamp'] > cutoff]
        
        # Check for suspicious patterns
        is_suspicious = len(activities) > SecurityManager.SUSPICIOUS_ACTIVITY_THRESHOLD
        
        if is_suspicious:
            logger.warning(
                f"Suspicious activity detected: User {user_id}, "
                f"Activity: {activity_type}, Count: {len(activities)}"
            )
        
        cache.set(cache_key, activities, 600)
        return is_suspicious


class RateLimiter:
    """Advanced rate limiting with different strategies"""
    
    @staticmethod
    def check_rate_limit(identifier: str, limit: int, window: int) -> Dict[str, Any]:
        """Check if request is within rate limit"""
        cache_key = f"rate_limit_{identifier}"
        requests = cache.get(cache_key, [])
        
        # Remove old requests outside the window
        cutoff = time.time() - window
        requests = [req for req in requests if req > cutoff]
        
        # Check if limit exceeded
        if len(requests) >= limit:
            return {
                'allowed': False,
                'requests': len(requests),
                'limit': limit,
                'reset_time': min(requests) + window
            }
        
        # Add current request
        requests.append(time.time())
        cache.set(cache_key, requests, window)
        
        return {
            'allowed': True,
            'requests': len(requests),
            'limit': limit,
            'remaining': limit - len(requests)
        }


def rate_limit(limit: int = 100, window: int = 3600, per: str = 'user'):
    """Rate limiting decorator"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Determine identifier based on 'per' parameter
            if per == 'user' and request.user.is_authenticated:
                identifier = f"user_{request.user.id}"
            elif per == 'ip':
                identifier = f"ip_{request.META.get('REMOTE_ADDR', 'unknown')}"
            else:
                identifier = f"global"
            
            # Check rate limit
            result = RateLimiter.check_rate_limit(identifier, limit, window)
            
            if not result['allowed']:
                logger.warning(
                    f"Rate limit exceeded: {identifier}, "
                    f"Limit: {limit}/{window}s"
                )
                return HttpResponseForbidden(
                    "Rate limit exceeded. Please try again later."
                )
            
            # Add rate limit headers
            response = view_func(request, *args, **kwargs)
            if hasattr(response, '__setitem__'):
                response['X-RateLimit-Limit'] = str(limit)
                response['X-RateLimit-Remaining'] = str(result.get('remaining', 0))
                response['X-RateLimit-Reset'] = str(int(result.get('reset_time', time.time())))
            
            return response
        
        return wrapper
    return decorator


class InputValidator:
    """Advanced input validation and sanitization"""
    
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
        r'expression\s*\(',  # CSS expressions
        r'@import',  # CSS imports
        r'<iframe[^>]*>',  # Iframes
        r'<object[^>]*>',  # Objects
        r'<embed[^>]*>',  # Embeds
    ]
    
    @classmethod
    def sanitize_input(cls, data: str) -> str:
        """Sanitize user input to prevent XSS and injection attacks"""
        import re
        
        if not isinstance(data, str):
            return data
        
        # Remove dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            data = re.sub(pattern, '', data, flags=re.IGNORECASE)
        
        # Encode HTML entities
        import html
        data = html.escape(data)
        
        return data
    
    @staticmethod
    def validate_file_upload(file) -> Dict[str, Any]:
        """Validate uploaded files for security"""
        ALLOWED_EXTENSIONS = {
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
            'documents': ['.pdf', '.doc', '.docx', '.txt', '.csv', '.xlsx'],
        }
        
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        
        if not file:
            return {'valid': False, 'error': 'No file provided'}
        
        # Check file size
        if file.size > MAX_FILE_SIZE:
            return {'valid': False, 'error': 'File too large (max 10MB)'}
        
        # Check file extension
        import os
        ext = os.path.splitext(file.name)[1].lower()
        all_allowed = sum(ALLOWED_EXTENSIONS.values(), [])
        
        if ext not in all_allowed:
            return {'valid': False, 'error': f'File type {ext} not allowed'}
        
        # Check for malicious content (basic)
        try:
            # Read first 1KB to check for suspicious content
            file.seek(0)
            content = file.read(1024).decode('utf-8', errors='ignore')
            file.seek(0)
            
            suspicious_patterns = ['<script', 'javascript:', 'vbscript:', '<?php']
            for pattern in suspicious_patterns:
                if pattern.lower() in content.lower():
                    return {'valid': False, 'error': 'Suspicious file content detected'}
        
        except Exception:
            # If we can't read the file, it might be binary (which is okay)
            pass
        
        return {'valid': True}


class AuditLogger:
    """Comprehensive audit logging for compliance"""
    
    @staticmethod
    def log_security_event(event_type: str, user_id: Optional[int], 
                          ip_address: str, details: Dict = None):
        """Log security-related events"""
        event = {
            'timestamp': timezone.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details or {},
            'severity': 'HIGH' if 'failed' in event_type.lower() else 'INFO'
        }
        
        logger.info(f"Security Event: {json.dumps(event)}")
        
        # Store in database for compliance
        try:
            from audit.models import AuditLog
            AuditLog.objects.create(
                user_id=user_id,
                action=event_type,
                ip_address=ip_address,
                metadata=event
            )
        except Exception as e:
            logger.error(f"Failed to store audit log: {e}")
    
    @staticmethod
    def log_data_access(user_id: int, resource_type: str, resource_id: str, 
                       action: str, ip_address: str):
        """Log data access for compliance (GDPR, SOX)"""
        AuditLogger.log_security_event(
            f"data_access_{action}",
            user_id,
            ip_address,
            {
                'resource_type': resource_type,
                'resource_id': resource_id,
                'action': action
            }
        )


def security_headers(view_func):
    """Add comprehensive security headers"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS (only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response
    
    return wrapper


def require_2fa(view_func):
    """Require two-factor authentication for sensitive operations"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user has 2FA enabled and verified
        if hasattr(request.user, 'profile') and request.user.profile.two_factor_enabled:
            session_key = f"2fa_verified_{request.user.id}"
            if not request.session.get(session_key):
                # Redirect to 2FA verification
                from django.shortcuts import redirect
                return redirect('users:verify_2fa')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper