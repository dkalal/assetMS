from django.contrib import admin
from .models import SystemSetting

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'setting_type', 'category', 'is_public', 'updated_at']
    list_filter = ['setting_type', 'category', 'is_public', 'updated_at']
    search_fields = ['key', 'value', 'description']
    readonly_fields = ['created_at', 'updated_at']

    def _is_global_operator(self, request):
        u = request.user
        return getattr(u, 'is_superuser', False) or getattr(u, 'is_system_admin', False)

    def has_module_permission(self, request):
        return self._is_global_operator(request)

    def has_view_permission(self, request, obj=None):
        return self._is_global_operator(request)

    def has_change_permission(self, request, obj=None):
        return self._is_global_operator(request)

    def has_add_permission(self, request):
        return self._is_global_operator(request)

    def has_delete_permission(self, request, obj=None):
        return self._is_global_operator(request)
