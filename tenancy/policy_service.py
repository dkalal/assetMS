"""
Multi-Tenancy Policy Service Layer
Centralized policy enforcement with caching and validation
"""
from typing import Optional
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError


class PolicyService:
    """
    Service layer for multi-tenancy policy enforcement.
    
    Provides centralized access to policy settings with caching,
    validation, and enforcement helpers.
    """
    
    CACHE_TIMEOUT = 3600  # 1 hour
    
    @staticmethod
    def get_policy(company):
        """
        Get policy for a company (cached).
        
        Args:
            company: Company instance or ID
            
        Returns:
            MultiTenancyPolicy instance or None
        """
        from tenancy.policy_models import MultiTenancyPolicy
        
        if company is None:
            return None
        
        return MultiTenancyPolicy.get_for_company(company)
    
    @staticmethod
    def is_branch_level_access_enabled(company) -> bool:
        """Check if branch-level access control is enabled for company"""
        policy = PolicyService.get_policy(company)
        return policy.branch_level_access if policy else True
    
    @staticmethod
    def is_cross_branch_transfer_allowed(company) -> bool:
        """Check if cross-branch transfers are allowed for company"""
        policy = PolicyService.get_policy(company)
        return policy.allow_cross_branch_transfers if policy else True
    
    @staticmethod
    def is_transfer_approval_required(company) -> bool:
        """Check if transfer approval workflow is required for company"""
        policy = PolicyService.get_policy(company)
        return policy.require_transfer_approval if policy else True
    
    @staticmethod
    def validate_cross_branch_transfer(company, from_branch, to_branch):
        """
        Validate if a cross-branch transfer is allowed.
        
        Args:
            company: Company instance
            from_branch: Source branch
            to_branch: Destination branch
            
        Raises:
            ValidationError: If cross-branch transfer is not allowed
        """
        # Same branch is always allowed
        if from_branch == to_branch:
            return
        
        # Check if different branches
        if from_branch and to_branch and from_branch.id != to_branch.id:
            if not PolicyService.is_cross_branch_transfer_allowed(company):
                raise ValidationError(
                    "Cross-branch transfers are disabled for your company. "
                    "Assets can only be transferred within the same branch."
                )
    
    @staticmethod
    def should_enforce_branch_scoping(user, company) -> bool:
        """
        Determine if branch-level scoping should be enforced for a user.
        
        Args:
            user: User instance
            company: Company instance
            
        Returns:
            bool: True if branch scoping should be enforced
        """
        # Admins always bypass branch restrictions
        if hasattr(user, 'role') and user.role == 'admin':
            return False
        
        # Check company policy
        policy = PolicyService.get_policy(company)
        if not policy or not policy.branch_level_access:
            return False
        
        # Enforce for managers and users
        return True
    
    @staticmethod
    def get_accessible_branches(user, company):
        """
        Get list of branch IDs accessible to a user based on policy.
        
        Args:
            user: User instance
            company: Company instance
            
        Returns:
            QuerySet or list of branch IDs
        """
        from tenancy.models import Branch, UserBranch
        
        # Admins see all branches
        if hasattr(user, 'role') and user.role == 'admin':
            return Branch.objects.filter(company=company, is_active=True).values_list('id', flat=True)
        
        # Check if branch scoping is enforced
        if not PolicyService.should_enforce_branch_scoping(user, company):
            return Branch.objects.filter(company=company, is_active=True).values_list('id', flat=True)
        
        # Get user's assigned branches
        user_branches = UserBranch.objects.filter(
            user=user,
            company=company,
            branch__is_active=True
        ).values_list('branch_id', flat=True)
        
        return list(user_branches)
    
    @staticmethod
    def update_policy(company, user, **kwargs):
        """
        Update policy settings with validation and audit logging.
        
        Args:
            company: Company instance
            user: User making the change (must be admin)
            **kwargs: Policy fields to update
            
        Returns:
            Updated MultiTenancyPolicy instance
            
        Raises:
            PermissionDenied: If user is not admin
            ValidationError: If invalid policy combination
        """
        from tenancy.policy_models import MultiTenancyPolicy
        from audit.utils import log_audit
        
        # Validate user is admin
        if not hasattr(user, 'role') or user.role != 'admin':
            raise PermissionDenied("Only administrators can modify multi-tenancy policies.")
        
        # Validate user belongs to company
        if hasattr(user, 'company_id') and user.company_id != company.id:
            raise PermissionDenied("You can only modify policies for your own company.")
        
        # Get or create policy
        policy = MultiTenancyPolicy.get_for_company(company)
        
        # Track changes for audit
        changes = []
        
        # Update allowed fields
        allowed_fields = ['branch_level_access', 'allow_cross_branch_transfers', 'require_transfer_approval']
        for field in allowed_fields:
            if field in kwargs:
                old_value = getattr(policy, field)
                new_value = kwargs[field]
                if old_value != new_value:
                    setattr(policy, field, new_value)
                    changes.append(f"{field}: {old_value} → {new_value}")
        
        # Update metadata
        policy.updated_by = user
        policy.save()
        
        # Log audit event
        if changes:
            log_audit(
                user,
                'policy_update',
                None,
                f"Updated multi-tenancy policy: {', '.join(changes)}",
                company=company,
                branch=None
            )
        
        return policy
    
    @staticmethod
    def get_policy_summary(company) -> dict:
        """
        Get human-readable policy summary.
        
        Args:
            company: Company instance
            
        Returns:
            Dictionary with policy status and descriptions
        """
        policy = PolicyService.get_policy(company)
        
        if not policy:
            return {
                'status': 'default',
                'message': 'Using default secure policies'
            }
        
        return {
            'status': 'configured',
            'data_isolation': {
                'enabled': True,
                'description': 'Complete data separation between companies (Always enforced)'
            },
            'branch_access': {
                'enabled': policy.branch_level_access,
                'description': 'Managers/users restricted to assigned branches' if policy.branch_level_access 
                              else 'Managers/users can access all company branches'
            },
            'cross_branch_transfers': {
                'enabled': policy.allow_cross_branch_transfers,
                'description': 'Assets can be transferred between branches' if policy.allow_cross_branch_transfers
                              else 'Assets can only be transferred within same branch'
            },
            'transfer_approval': {
                'enabled': policy.require_transfer_approval,
                'description': 'Transfers require approval workflow' if policy.require_transfer_approval
                              else 'Transfers are completed immediately'
            }
        }


# Singleton instance
policy_service = PolicyService()

__all__ = ['PolicyService', 'policy_service']
