from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (BaseUserAdmin.fieldsets or tuple()) + (
        ('Role', {'fields': ('role',)}),
    )
    list_display = (BaseUserAdmin.list_display or tuple()) + ('role',)
    list_filter = (BaseUserAdmin.list_filter or tuple()) + ('role',)
