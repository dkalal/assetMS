"""
Custom Authentication Backends
============================
Purpose: Email-based authentication for modern SaaS login experience
Following world-class standards: Slack, Asana, Salesforce, ServiceNow
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend that allows login with either email or username.
    
    This provides flexibility for:
    - New users: Login with email (modern SaaS standard)
    - Legacy users: Login with username (backward compatibility)
    
    Following patterns from:
    - Slack: Email-based login
    - Asana: Email-based login
    - Salesforce: Email-based login
    - ServiceNow: Email or username
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user by email or username.
        
        Args:
            request: HttpRequest object
            username: Can be either email address or username
            password: User password
            **kwargs: Additional keyword arguments
            
        Returns:
            User object if authentication succeeds, None otherwise
        """
        if username is None or password is None:
            return None
        
        try:
            # Try to find user by email first (modern SaaS standard)
            # Then fallback to username for backward compatibility
            user = User.objects.get(
                Q(email__iexact=username) | Q(username__iexact=username)
            )
        except User.DoesNotExist:
            # Run default password hasher to prevent timing attacks
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # Edge case: Multiple users with same email (shouldn't happen, but handle gracefully)
            # Prefer email match over username match
            user = User.objects.filter(email__iexact=username).first()
            if not user:
                user = User.objects.filter(username__iexact=username).first()
        
        if user and user.check_password(password):
            # Check if account is active
            if not user.is_active:
                return None
            
            # Check if account is locked
            if hasattr(user, 'account_locked_until') and user.account_locked_until:
                from django.utils import timezone
                if timezone.now() < user.account_locked_until:
                    return None  # Account is locked
            
            return user
        
        return None
    
    def get_user(self, user_id):
        """
        Retrieve user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None





