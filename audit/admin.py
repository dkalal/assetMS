from django.contrib import admin
from .models import AuditLog, AuditEvent

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'asset', 'timestamp')
    list_filter = ('action', 'user')
    search_fields = ('details',)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'severity', 'company', 'timestamp')
    list_filter = ('action', 'severity', 'company', 'timestamp')
    search_fields = ('description', 'user__username', 'user__email')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('company', 'user', 'action', 'severity', 'description')
        }),
        ('Context', {
            'fields': ('ip_address', 'user_agent', 'metadata')
        }),
        ('Related Objects', {
            'fields': ('related_user', 'related_asset'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def has_add_permission(self, request):
        # Audit events should only be created programmatically
        return False
    
    def has_change_permission(self, request, obj=None):
        # Audit events should be immutable
        return False
