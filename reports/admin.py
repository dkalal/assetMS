from django.contrib import admin
from .models import Report
from tenancy.admin_mixins import CompanyScopedAdmin

@admin.register(Report)
class ReportAdmin(CompanyScopedAdmin):
    list_display = ('report_type', 'created_by', 'created_at')
    list_filter = ('report_type', 'created_by')
    search_fields = ('file',)
