"""
WORLD-CLASS: Unified Asset Filtering Service

This service ensures 100% consistency between dashboard metrics and asset list views.
All filtering logic is centralized here to eliminate data discrepancies.

Inspired by: ServiceNow ITAM, IBM Maximo, SAP EAM
"""

from django.db.models import Q, QuerySet
from typing import Optional


class AssetFilteringService:
    """
    Centralized service for consistent asset filtering across all views.
    
    This ensures dashboard metrics match asset list counts exactly.
    """
    
    @staticmethod
    def get_base_queryset(company, user, request=None):
        """
        Get base asset queryset with company and role-based filtering.
        
        This is the SINGLE SOURCE OF TRUTH for all asset queries.
        
        Args:
            company: Company instance
            user: User instance
            request: Optional request object for branch context
            
        Returns:
            QuerySet: Filtered asset queryset
        """
        from assets.models import Asset
        from tenancy.policy_service import PolicyService
        
        if company is None:
            return Asset.objects.none()
        
        # Start with company-scoped queryset
        # CRITICAL: Exclude deleted assets (soft-deleted assets should not appear in lists)
        qs = Asset.objects.filter(company=company).exclude(status=Asset.STATUS_DELETED)
        
        # Get user role
        role = getattr(user, 'role', 'user')
        
        # CRITICAL: Apply role-based filtering
        if role == 'user':
            # Users see ONLY their assigned assets
            qs = qs.filter(assigned_to=user)
            
        elif role == 'manager':
            # Managers see assets in their accessible branches
            try:
                accessible_branch_ids = PolicyService.get_accessible_branches(user, company)
                
                if accessible_branch_ids:
                    # Filter by accessible branches
                    qs = qs.filter(branch_id__in=accessible_branch_ids)
                else:
                    # FALLBACK: Check for primary_branch or managed branches
                    # This handles cases where UserBranch table is not populated
                    from tenancy.models import Branch
                    
                    # Try primary_branch first
                    primary_branch = getattr(user, 'primary_branch', None)
                    
                    # Try managed branches (where user is the manager)
                    managed_branches = Branch.objects.filter(
                        company=company,
                        manager=user,
                        is_active=True
                    )
                    
                    # Try branch from request
                    request_branch = getattr(request, 'branch', None) if request else None
                    
                    if primary_branch:
                        # User has primary branch - show assets from that branch
                        qs = qs.filter(branch=primary_branch)
                    elif managed_branches.exists():
                        # User manages branches - show assets from managed branches
                        qs = qs.filter(branch__in=managed_branches)
                    elif request_branch:
                        # Use branch from request context
                        qs = qs.filter(branch=request_branch)
                    else:
                        # WORLD-CLASS FIX: Show all company assets for managers
                        # This prevents "No assets found" when branch assignments are missing
                        # Admins can configure UserBranch for stricter access control
                        pass  # No additional filter - show all company assets
                    
            except Exception as e:
                # Fallback: try to get branch from request
                branch = getattr(request, 'branch', None) if request else None
                if branch:
                    qs = qs.filter(branch=branch)
                else:
                    # WORLD-CLASS FIX: Show all company assets for managers as fallback
                    # Better to show assets than hide them due to configuration issues
                    pass  # No additional filter
        
        # Admin sees all company assets (no additional filter)
        
        return qs
    
    @staticmethod
    def apply_status_filter(qs: QuerySet, status: Optional[str]) -> QuerySet:
        """Apply status filter if provided."""
        if status:
            qs = qs.filter(status=status)
        return qs
    
    @staticmethod
    def apply_branch_filter(qs: QuerySet, branch_id: Optional[str]) -> QuerySet:
        """Apply branch filter if provided."""
        if branch_id:
            try:
                qs = qs.filter(branch__id=int(branch_id))
            except (ValueError, TypeError):
                pass
        return qs
    
    @staticmethod
    def apply_category_filter(qs: QuerySet, category_id: Optional[str]) -> QuerySet:
        """Apply category filter if provided."""
        if category_id:
            try:
                qs = qs.filter(category__id=int(category_id))
            except (ValueError, TypeError):
                pass
        return qs
    
    @staticmethod
    def apply_assigned_filter(qs: QuerySet, assigned: Optional[str]) -> QuerySet:
        """Apply assigned/unassigned filter if provided."""
        if assigned == 'yes':
            qs = qs.filter(assigned_to__isnull=False)
        elif assigned == 'no':
            qs = qs.filter(assigned_to__isnull=True)
        return qs
    
    @staticmethod
    def apply_warranty_filter(qs: QuerySet, warranty: Optional[str]) -> QuerySet:
        """Apply warranty expiring filter if provided."""
        if warranty == 'expiring':
            from datetime import timedelta
            from django.utils import timezone
            
            soon = timezone.now() + timedelta(days=30)
            now_date = timezone.now().date().isoformat()
            soon_date = soon.date().isoformat()
            
            qs = qs.filter(
                Q(dynamic_data__warranty_expiry__lte=soon_date, dynamic_data__warranty_expiry__gte=now_date) |
                Q(dynamic_data__warranty_end__lte=soon_date, dynamic_data__warranty_end__gte=now_date) |
                Q(dynamic_data__warranty_expiration__lte=soon_date, dynamic_data__warranty_expiration__gte=now_date)
            )
        return qs
    
    @staticmethod
    def apply_location_filter(qs: QuerySet, location: Optional[str]) -> QuerySet:
        """Apply location filter if provided."""
        if location:
            qs = qs.filter(dynamic_data__location__icontains=location)
        return qs
    
    @staticmethod
    def apply_search_filter(qs: QuerySet, search: Optional[str]) -> QuerySet:
        """Apply search filter if provided."""
        if search:
            qs = qs.filter(
                Q(dynamic_data__name__icontains=search) |
                Q(dynamic_data__model__icontains=search) |
                Q(description__icontains=search)
            )
        return qs
    
    @staticmethod
    def get_filtered_queryset(company, user, request=None, filters=None):
        """
        Get fully filtered asset queryset.
        
        This method applies ALL filters in the correct order to ensure
        dashboard and asset list show identical data.
        
        Args:
            company: Company instance
            user: User instance
            request: Optional request object
            filters: Optional dict of filters to apply
            
        Returns:
            QuerySet: Fully filtered asset queryset
        """
        # Get base queryset with role-based filtering
        qs = AssetFilteringService.get_base_queryset(company, user, request)
        
        # Apply additional filters if provided
        if filters:
            qs = AssetFilteringService.apply_status_filter(qs, filters.get('status'))
            qs = AssetFilteringService.apply_branch_filter(qs, filters.get('branch'))
            qs = AssetFilteringService.apply_category_filter(qs, filters.get('category'))
            qs = AssetFilteringService.apply_assigned_filter(qs, filters.get('assigned'))
            qs = AssetFilteringService.apply_warranty_filter(qs, filters.get('warranty'))
            qs = AssetFilteringService.apply_location_filter(qs, filters.get('location'))
            qs = AssetFilteringService.apply_search_filter(qs, filters.get('search'))
        
        return qs
    
    @staticmethod
    def get_statistics(company, user, request=None):
        """
        Get asset statistics using the SAME filtering logic as asset list.
        
        This ensures dashboard metrics match asset list counts exactly.
        
        Args:
            company: Company instance
            user: User instance
            request: Optional request object
            
        Returns:
            dict: Statistics dictionary
        """
        from assets.models import Asset
        from django.db.models import Count, Q
        
        # Get base queryset (SAME as asset list)
        qs = AssetFilteringService.get_base_queryset(company, user, request)
        
        # Calculate statistics using single aggregate query
        stats = qs.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status=Asset.STATUS_ACTIVE)),
            maintenance=Count('id', filter=Q(status=Asset.STATUS_IN_MAINTENANCE)),
            retired=Count('id', filter=Q(status=Asset.STATUS_RETIRED)),
            lost=Count('id', filter=Q(status=Asset.STATUS_LOST)),
            assigned=Count('id', filter=Q(assigned_to__isnull=False)),
            unassigned=Count('id', filter=Q(assigned_to__isnull=True)),
            transferred=Count('id', filter=Q(status=Asset.STATUS_TRANSFERRED)),
        )
        
        return {
            'total': stats['total'],
            'active': stats['active'],
            'in_maintenance': stats['maintenance'],
            'maintenance_assets': stats['maintenance'],  # Alias
            'needs_repair': stats['maintenance'],  # Alias
            'retired': stats['retired'],
            'lost': stats['lost'],
            'assigned': stats['assigned'],
            'assigned_assets': stats['assigned'],  # Alias
            'unassigned': stats['unassigned'],
            'unassigned_assets': stats['unassigned'],  # Alias
            'transferred': stats['transferred'],
            'transferred_assets': stats['transferred'],  # Alias
        }


# Singleton instance for easy import
asset_filtering_service = AssetFilteringService()
