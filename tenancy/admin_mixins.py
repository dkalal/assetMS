from django.contrib import admin
from django.contrib.auth import get_user_model
from tenancy.models import Company, Branch

User = get_user_model()

class CompanyScopedAdmin(admin.ModelAdmin):
    """Admin mixin that enforces company-level data isolation for non-system admins.

    Rules:
    - Global operators (is_superuser or is_system_admin) can see everything.
    - Company-scoped users see only rows filtered by their company (on `company_field`).
    - Foreign key choices for company/branch/user are limited to the user's company.
    """

    # Name of the model field that points to Company (commonly 'company')
    company_field = 'company'

    def _is_global_operator(self, request):
        u = request.user
        return getattr(u, 'is_superuser', False) or getattr(u, 'is_system_admin', False)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self._is_global_operator(request):
            return qs
        company = getattr(request.user, 'company', None)
        if not company:
            return qs.none()
        # Filter by provided company_field if present on model
        if hasattr(self.model, self.company_field):
            return qs.filter(**{self.company_field: company})
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not self._is_global_operator(request):
            company = getattr(request.user, 'company', None)
            if company:
                if db_field.name == 'company':
                    kwargs['queryset'] = Company.objects.filter(pk=company.pk)
                elif db_field.name in ('branch', 'from_branch', 'to_branch'):
                    kwargs['queryset'] = Branch.objects.filter(company=company)
                elif db_field.name == 'category':
                    # Lazy import to avoid circular import (assets.admin -> tenancy.admin_mixins)
                    from assets.models import AssetCategory  # local import
                    kwargs['queryset'] = AssetCategory.objects.filter(company=company)
                elif db_field.name in (
                    'assigned_to', 'user', 'manager', 'recipient', 'from_user', 'to_user',
                    'processed_by', 'requested_by', 'reviewed_by', 'completed_by', 'created_by',
                    'updated_by', 'approved_by', 'performed_by', 'supervisor', 'retired_by',
                    'initiator'
                ):
                    kwargs['queryset'] = User.objects.filter(company=company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
