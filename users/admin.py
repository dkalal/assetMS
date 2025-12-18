from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (BaseUserAdmin.fieldsets or tuple()) + (
        ('Role', {'fields': ('role', 'is_system_admin')}),
    )
    list_display = (BaseUserAdmin.list_display or tuple()) + ('role', 'company', 'is_system_admin')
    list_filter = (BaseUserAdmin.list_filter or tuple()) + ('role', 'company', 'is_system_admin')

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
        return qs.filter(company=company)

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if not self._is_global_operator(request):
            ro += ['is_system_admin', 'is_superuser', 'is_staff', 'groups', 'user_permissions', 'company']
        return ro
