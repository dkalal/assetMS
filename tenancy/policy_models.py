"""
Multi-Tenancy Policy Models
Enterprise-grade policy management for granular multi-tenancy controls
"""
from django.db import models
from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver


class MultiTenancyPolicy(models.Model):
    """
    Per-company multi-tenancy enforcement policies.
    
    Inspired by ServiceNow ITAM, IBM Maximo, and SAP EAM policy frameworks.
    Provides granular control over data isolation, branch access, and transfer workflows.
    """
    
    company = models.OneToOneField(
        'tenancy.Company',
        on_delete=models.CASCADE,
        related_name='tenancy_policy',
        help_text="Company this policy applies to"
    )
    
    # Data Isolation (Always Enforced - Non-Configurable)
    enforce_data_isolation = models.BooleanField(
        default=True,
        editable=False,
        help_text="Ensures complete data separation between companies (Always enabled for security)"
    )
    
    # Branch-Level Access Control
    branch_level_access = models.BooleanField(
        default=True,
        help_text="Restrict managers and users to their assigned branches only. "
                  "When enabled, users can only view/manage assets in branches they're assigned to. "
                  "Admins always have company-wide access."
    )
    
    # Cross-Branch Operations
    allow_cross_branch_transfers = models.BooleanField(
        default=True,
        help_text="Enable asset transfers between different branches within the same company. "
                  "When disabled, assets can only be transferred within the same branch."
    )
    
    # Transfer Approval Requirements
    require_transfer_approval = models.BooleanField(
        default=True,
        help_text="All asset transfers must go through the approval workflow (Receiver → Admin). "
                  "When disabled, transfers are completed immediately without approval."
    )
    
    # Metadata & Audit Trail
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policy_updates',
        help_text="Last admin who modified this policy"
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Multi-Tenancy Policy"
        verbose_name_plural = "Multi-Tenancy Policies"
        ordering = ['company__name']
        indexes = [
            models.Index(fields=['company'], name='policy_company_idx'),
        ]
    
    def __str__(self):
        return f"Policy for {self.company.name}"
    
    def get_cache_key(self):
        """Generate cache key for this policy"""
        return f"tenancy_policy_{self.company_id}"
    
    def invalidate_cache(self):
        """Invalidate cached policy"""
        cache.delete(self.get_cache_key())
    
    @classmethod
    def get_for_company(cls, company):
        """
        Get or create policy for a company with caching.
        
        Args:
            company: Company instance or ID
            
        Returns:
            MultiTenancyPolicy instance
        """
        if company is None:
            return None
        
        company_id = company.id if hasattr(company, 'id') else company
        cache_key = f"tenancy_policy_{company_id}"
        
        # Try cache first
        policy = cache.get(cache_key)
        if policy is not None:
            return policy
        
        # Get or create from database
        policy, created = cls.objects.get_or_create(
            company_id=company_id,
            defaults={
                'enforce_data_isolation': True,
                'branch_level_access': True,
                'allow_cross_branch_transfers': True,
                'require_transfer_approval': True,
            }
        )
        
        # Cache for 1 hour
        cache.set(cache_key, policy, 3600)
        
        return policy
    
    def to_dict(self):
        """Serialize policy to dictionary for API responses"""
        return {
            'company_id': self.company_id,
            'company_name': self.company.name,
            'enforce_data_isolation': self.enforce_data_isolation,
            'branch_level_access': self.branch_level_access,
            'allow_cross_branch_transfers': self.allow_cross_branch_transfers,
            'require_transfer_approval': self.require_transfer_approval,
            'updated_by': self.updated_by.get_full_name() if self.updated_by else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@receiver(post_save, sender=MultiTenancyPolicy)
def invalidate_policy_cache(sender, instance, **kwargs):
    """Automatically invalidate cache when policy is updated"""
    instance.invalidate_cache()


# Import in tenancy/models.py to register the model
__all__ = ['MultiTenancyPolicy']
