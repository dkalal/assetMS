from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'asset', 'timestamp')
    list_filter = ('action', 'user')
    search_fields = ('details',)
