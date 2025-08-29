from django.contrib import admin
from .models import SystemSetting

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'setting_type', 'category', 'is_public', 'updated_at']
    list_filter = ['setting_type', 'category', 'is_public', 'updated_at']
    search_fields = ['key', 'value', 'description']
    readonly_fields = ['created_at', 'updated_at']
